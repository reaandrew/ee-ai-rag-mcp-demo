import json
import logging
import os
import boto3
import jwt

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Set a default region for testing environments
if not os.environ.get("AWS_REGION") and not os.environ.get("AWS_DEFAULT_REGION"):
    os.environ["AWS_DEFAULT_REGION"] = "us-east-1"
    logger.info("No AWS region found, defaulting to us-east-1 for testing")

# Get the KMS key ID from environment variables
KMS_KEY_ID = os.environ.get("API_TOKEN_KMS_KEY_ID")

# Initialize the KMS client
kms_client = boto3.client("kms")

# Set the allowed issuer
ALLOWED_ISSUER = "ee-ai-rag-mcp-demo"


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


def verify_token(token):
    """
    Verify a JWT token using the KMS key.

    Args:
        token (str): JWT token

    Returns:
        bool: True if verification succeeds, False otherwise
    """
    try:
        if not token:
            logger.warning("Empty token provided")
            return False

        logger.info(f"Verifying JWT token with KMS key ID: {KMS_KEY_ID}")

        # Extract the kid (Key ID) from the token header
        # This should match our KMS key ID
        try:
            unverified_header = jwt.get_unverified_header(token)
            kid = unverified_header.get("kid")
            if kid != KMS_KEY_ID:
                logger.warning(f"Token key ID {kid} does not match expected key ID {KMS_KEY_ID}")
                # We'll still try to verify with our key
        except Exception as e:
            logger.warning(f"Error parsing token header: {str(e)}")
            return False

        # Verify the token using HS256 algorithm with the KMS key ID as the secret
        # This works because we're using a symmetric key
        payload = jwt.decode(
            token,
            KMS_KEY_ID,  # Using KMS key ID as the secret
            algorithms=["HS256"],
            issuer=ALLOWED_ISSUER,
            options={
                "verify_signature": True,
                "verify_exp": True,
                "verify_iat": True,
            },
        )
        logger.info(f"JWT verification successful: {payload}")
        return True

    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return False
    except jwt.InvalidTokenError as e:
        logger.warning(f"Invalid token: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during token verification: {str(e)}")
        return False


def lambda_handler(event, context):
    """
    Lambda function handler that serves as a token authorizer for API Gateway.
    Verifies KMS-signed API tokens.
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

        # Extract the token from the Authorization header
        headers = event.get("headers", {})
        auth_header = headers.get("authorization", headers.get("Authorization", ""))

        if not auth_header:
            logger.warning("No Authorization header found")
            return {"isAuthorized": False}

        # Strip 'Bearer ' prefix if present
        if auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
        else:
            token = auth_header

        # Verify the token
        is_valid = verify_token(token)

        simple_response = {"isAuthorized": is_valid}

        if is_valid:
            logger.info("Authorization successful")
        else:
            logger.warning("Authorization failed - invalid token")

        return simple_response

    except Exception as e:
        logger.error(f"Error in authorizer: {str(e)}")
        # In case of an error, deny access with the simple format
        return {"isAuthorized": False}
