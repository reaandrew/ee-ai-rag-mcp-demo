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

        # Get all documents with their latest status
        status = {"documents": tracking_utils.get_all_documents()}

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
