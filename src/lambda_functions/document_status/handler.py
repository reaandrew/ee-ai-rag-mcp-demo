import json
import logging
import decimal


# Helper class to convert Decimal objects to int/float for JSON serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            # Convert decimals to integers or floats
            if o % 1 == 0:
                return int(o)
            else:
                return float(o)
        return super(DecimalEncoder, self).default(o)


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

# Constants
CONTENT_TYPE_JSON = "application/json"
CONTENT_TYPE_PLAIN = "text/plain"
CORS_HEADERS_VALUE = "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"

# Define a common CORS headers variable
CORS_HEADERS = {
    "Content-Type": CONTENT_TYPE_JSON,
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": CORS_HEADERS_VALUE,
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

        # Validate httpMethod exists
        if "httpMethod" not in event:
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps({"error": "Missing httpMethod in event"}, cls=DecimalEncoder),
            }

        # Handle OPTIONS method for CORS preflight requests
        if event["httpMethod"] == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": CORS_HEADERS,
                "body": json.dumps(
                    {"message": "CORS preflight request successful"}, cls=DecimalEncoder
                ),
            }

        # We only support GET for document status
        if event["httpMethod"] != "GET":
            return {
                "statusCode": 400,
                "headers": CORS_HEADERS,
                "body": json.dumps(
                    {"error": f"Unsupported method: {event['httpMethod']}"}, cls=DecimalEncoder
                ),
            }

        # Check if tracking is available
        if not tracking_utils:
            return {
                "statusCode": 500,
                "headers": CORS_HEADERS,
                "body": json.dumps(
                    {"error": "Document tracking is not available"}, cls=DecimalEncoder
                ),
            }

        # Get all documents with their latest status
        status = {"documents": tracking_utils.get_all_documents()}

        return {
            "statusCode": 200,
            "headers": CORS_HEADERS,
            "body": json.dumps(status, cls=DecimalEncoder),
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "headers": CORS_HEADERS,
            "body": json.dumps(
                {"error": f"An error occurred while checking document status: {str(e)}"},
                cls=DecimalEncoder,
            ),
        }
