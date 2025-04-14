import json
import logging

# import os  # Not directly used

try:
    # Try to import tracking utils
    from utils import tracking_utils
except ImportError:
    try:
        # When running locally or in tests with src structure
        from src.utils import tracking_utils
    except ImportError:
        try:
            # Absolute import (sometimes needed in Lambda)
            import utils.tracking_utils as tracking_utils
        except ImportError:
            # Define a fallback for tracking in case import fails
            tracking_utils = None
            logging.error(
                "Could not import tracking_utils module, document status will be unavailable"
            )

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Define a common CORS headers variable
CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": (
        "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
    ),
}


def lambda_handler(event, context):
    """
    Lambda function handler that returns document processing status.

    Args:
        event (dict): Event from API Gateway
        context (LambdaContext): Lambda context

    Returns:
        dict: Status response
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Extract parameters from the request
        if (
            "pathParameters" in event
            and event["pathParameters"]
            and "document_id" in event["pathParameters"]
        ):
            # Path parameter: /status/{document_id}
            document_id = event["pathParameters"]["document_id"]
            use_base_id = True
        elif "queryStringParameters" in event and event["queryStringParameters"]:
            # Query parameter: /status?document_id=xxx&use_base_id=true
            document_id = event["queryStringParameters"].get("document_id")
            use_base_id_str = event["queryStringParameters"].get("use_base_id", "true")
            use_base_id = use_base_id_str.lower() == "true"
        else:
            # Body parameter from POST
            try:
                body = json.loads(event.get("body", "{}"))
                document_id = body.get("document_id")
                use_base_id = body.get("use_base_id", True)
            except json.JSONDecodeError:
                return {
                    "statusCode": 400,
                    "headers": CORS_HEADERS,
                    "body": json.dumps({"error": "Invalid JSON in request body"}),
                }

        if not document_id:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Missing document_id parameter"}),
            }

        # Handle OPTIONS method for CORS preflight requests
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps({"message": "CORS preflight request successful"}),
            }

        # Check if tracking is available
        if not tracking_utils:
            return {
                "statusCode": 500,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Document tracking is not available"}),
            }

        # Get document status
        if use_base_id:
            # Get status for all versions of this document
            status = tracking_utils.get_processing_status(document_id)
        else:
            # Get status for a specific document ID/version
            # Retrieve the specific record and format it
            base_id_parts = document_id.split("/")
            if len(base_id_parts) >= 2:
                base_doc_id = base_id_parts[0] + "/" + base_id_parts[1]
            else:
                base_doc_id = document_id

            records = tracking_utils.get_document_history(base_doc_id)
            record = next((r for r in records if r.get("document_id") == document_id), None)

            if record:
                status = {
                    "document_name": record.get("document_name", "Unknown"),
                    "document_version": record.get("document_version"),
                    "status": record.get("status"),
                    "progress": (
                        f"{record.get('indexed_chunks', 0)}/{record.get('total_chunks', 0)}"
                    ),
                    "start_time": record.get("start_time"),
                    "completion_time": record.get("completion_time", "N/A"),
                }
            else:
                status = {
                    "status": "NOT_FOUND",
                    "message": f"No record found for document ID: {document_id}",
                }

        return {"statusCode": 200, "headers": CORS_HEADERS, "body": json.dumps(status)}

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"error": f"An error occurred while checking document status: {str(e)}"}
            ),
        }
