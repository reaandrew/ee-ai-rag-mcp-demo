import json
import logging

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)


def lambda_handler(event, context):
    """
    Lambda function handler that serves as a simple authorizer for API Gateway.
    This is a placeholder implementation that always authorizes the request.

    Args:
        event (dict): Event data from API Gateway
        context (LambdaContext): Lambda context

    Returns:
        dict: IAM policy document for API Gateway
    """
    try:
        logger.info(f"Received authorization event: {json.dumps(event)}")

        # Extract request details
        request_context = event.get("requestContext", {})
        http_method = request_context.get("http", {}).get("method", "")
        resource_path = request_context.get("http", {}).get("path", "")

        # For audit logging purposes
        source_ip = request_context.get("identity", {}).get("sourceIp", "unknown")
        user_agent = request_context.get("identity", {}).get("userAgent", "unknown")

        logger.info(f"Authorization request from IP: {source_ip}, User-Agent: {user_agent}")
        logger.info(f"Method: {http_method}, Path: {resource_path}")

        # In this placeholder implementation, always authorize the request
        # In a real implementation, you would check for valid API keys, tokens, etc.

        # Construct the response policy document
        policy_document = {
            "principalId": "user",
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Allow",
                        "Resource": event.get("routeArn", "*"),
                    }
                ],
            },
            # You can pass additional context to the backend
            "context": {"stringKey": "value", "numberKey": 123, "booleanKey": True},
        }

        logger.info("Authorization successful")
        return policy_document

    except Exception as e:
        logger.error(f"Error in authorizer: {str(e)}")
        # In case of an error, deny access
        return {
            "principalId": "user",
            "policyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Action": "execute-api:Invoke",
                        "Effect": "Deny",
                        "Resource": event.get("routeArn", "*"),
                    }
                ],
            },
        }
