import json
import logging
import os
import base64
import boto3
from botocore.exceptions import ClientError

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
    Verify the signed API token using the KMS key.

    Args:
        token (str): Base64-encoded token containing both UUID and signature

    Returns:
        bool: True if verification succeeds, False otherwise
    """
    try:
        if not token:
            logger.warning("Empty token provided")
            return False

        # Enhanced debugging
        logger.info(f"Verifying token with KMS key ID: {KMS_KEY_ID}")

        # Split the token into parts (token_id:signature)
        try:
            # Add padding if needed for base64 decoding
            padded_token = token
            padding = len(padded_token) % 4
            if padding:
                padded_token += "=" * (4 - padding)

            logger.info(f"Padded token length: {len(padded_token)}")

            # Decode the base64 token
            decoded_bytes = base64.b64decode(padded_token)
            decoded = decoded_bytes.decode("utf-8")

            logger.info(f"Decoded token length: {len(decoded)}")

            # Split the parts
            parts = decoded.split(":")

            if len(parts) != 2:
                logger.warning(f"Invalid token format: expected 2 parts, got {len(parts)}")
                return False

            token_id, signature = parts
            logger.info(f"Token ID length: {len(token_id)}, Signature length: {len(signature)}")

            # Add padding to signature if needed
            padded_signature = signature
            sig_padding = len(padded_signature) % 4
            if sig_padding:
                padded_signature += "=" * (4 - sig_padding)

            # Base64 decode the signature
            binary_signature = base64.b64decode(padded_signature)
            logger.info(f"Binary signature length: {len(binary_signature)} bytes")

            # Verify the signature with KMS
            try:
                response = kms_client.verify(
                    KeyId=KMS_KEY_ID,
                    Message=token_id.encode("utf-8"),
                    Signature=binary_signature,
                    SigningAlgorithm="RSASSA_PKCS1_V1_5_SHA_256",
                )
                is_valid = response.get("SignatureValid", False)
                logger.info(f"KMS verification result: {is_valid}")
                return is_valid

            except ClientError as kms_err:
                logger.error(f"KMS verification error: {str(kms_err)}")
                # Check if we can get more details
                if hasattr(kms_err, "response"):
                    logger.error(f"KMS error response: {kms_err.response}")
                return False

        except Exception as e:
            logger.error(f"Error parsing token: {str(e)}")
            return False

    except ClientError as e:
        logger.error(f"AWS KMS error: {str(e)}")
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
