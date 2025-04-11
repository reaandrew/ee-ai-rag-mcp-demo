import json
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def extract_method_path(event):
    """
    Extract method and path from the event for logging.

    Args:
        event (dict): API Gateway event

    Returns:
        tuple: (http_method, resource_path, source_ip, user_agent)
    """
    request_context = event.get("requestContext", {})
    http_context = request_context.get("http", {})
    http_method = http_context.get("method", "")
    resource_path = http_context.get("path", "")

    # For audit logging purposes - HTTP API format
    source_ip = http_context.get("sourceIp", "unknown")
    user_agent = http_context.get("userAgent", "unknown")

    return http_method, resource_path, source_ip, user_agent


def lambda_handler(event, context):
    """
    Lambda function handler that serves as a simple authorizer for API Gateway.
    This is a placeholder implementation that always authorizes the request.
    Uses HTTP API v2 format with payload version 2.0.

    Args:
        event (dict): Event data from API Gateway
        context (LambdaContext): Lambda context

    Returns:
        dict: Simple response with isAuthorized flag for HTTP API v2
    """
    try:
        logger.info(f"Received authorization event: {json.dumps(event)}")

        # Extract request details
        http_method, resource_path, source_ip, user_agent = extract_method_path(event)

        logger.info(f"Authorization request from IP: {source_ip}, User-Agent: {user_agent}")
        logger.info(f"Method: {http_method}, Path: {resource_path}")

        # In this placeholder implementation, always authorize the request
        # In a real implementation, you would check for valid API keys, tokens, etc.

        # For HTTP API with payload format version 2.0, we need to return a simple response
        # with just the isAuthorized flag (no policy document needed)
        simple_response = {
            "isAuthorized": True
            # No context needed for this simple authorizer
        }

        logger.info("Authorization successful")
        return simple_response

    except Exception as e:
        logger.error(f"Error in authorizer: {str(e)}")
        # In case of an error, deny access with the simple format
        return {"isAuthorized": False}
