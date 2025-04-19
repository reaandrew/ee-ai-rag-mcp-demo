import json
import unittest
import os
import jwt
from unittest.mock import patch, MagicMock

import pytest
import boto3
from src.lambda_functions.auth_authorizer import handler


@pytest.fixture(autouse=True)
def mock_boto3_and_env():
    """Mock boto3 client and environment variables for all tests"""
    # Mock KMS client
    mock_kms = MagicMock()

    with patch("boto3.client") as mock_client:
        mock_client.return_value = mock_kms

        # Mock environment variables
        with patch.dict(
            os.environ, {"API_TOKEN_KMS_KEY_ID": "test-key-id", "AWS_DEFAULT_REGION": "us-east-1"}
        ):
            yield


@pytest.fixture
def api_gateway_event():
    """Create a sample API Gateway authorizer event"""
    return {
        "version": "2.0",
        "type": "REQUEST",
        "routeArn": "arn:aws:execute-api:eu-west-2:123456789012:abcdef123/test/POST/search",
        "identitySource": ["Bearer token123"],
        "routeKey": "POST /search",
        "rawPath": "/search",
        "rawQueryString": "",
        "headers": {"Authorization": "Bearer token123", "Content-Type": "application/json"},
        "requestContext": {
            "accountId": "123456789012",
            "apiId": "abcdef123",
            "domainName": "abcdef123.execute-api.eu-west-2.amazonaws.com",
            "domainPrefix": "abcdef123",
            "http": {
                "method": "POST",
                "path": "/search",
                "protocol": "HTTP/1.1",
                "sourceIp": "192.168.0.1",
                "userAgent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            },
            "requestId": "request-id",
            "routeKey": "POST /search",
            "stage": "test",
            "time": "03/Oct/2022:00:00:00 +0000",
            "timeEpoch": 1664755200000,
        },
        "body": '{"query":"test query"}',
        "isBase64Encoded": False,
    }


def test_lambda_handler_success(api_gateway_event):
    """Test successful authorization"""
    # Mock the verify_token function to return True
    with patch.object(handler, "verify_token", return_value=True):
        # Mock logging to avoid interference
        with patch.object(handler.logger, "info"):
            response = handler.lambda_handler(api_gateway_event, {})

    # Verify response structure for HTTP API v2 format
    assert "isAuthorized" in response
    assert response["isAuthorized"] is True


def test_lambda_handler_invalid_token(api_gateway_event):
    """Test failed authorization with invalid token - covers line 148"""
    # Mock the verify_token function to return False (invalid token)
    with patch.object(handler, "verify_token", return_value=False):
        # Mock logging to capture the warning
        with patch.object(handler.logger, "info"):
            with patch.object(handler.logger, "warning") as mock_warning:
                response = handler.lambda_handler(api_gateway_event, {})

    # Verify response structure for HTTP API v2 format
    assert "isAuthorized" in response
    assert response["isAuthorized"] is False

    # Verify the specific warning message for failed authorization (line 148)
    mock_warning.assert_called_with("Authorization failed - invalid token")


def test_lambda_handler_error():
    """Test error handling"""
    # Create event that will cause an error - this will throw an exception when
    # we try to access httpMethod because it's a different structure than expected
    event = {"requestContext": {"broken": "structure"}}

    # Mock logging to avoid interference
    with patch.object(handler.logger, "info"), patch.object(handler.logger, "error"):
        # Cause an actual error to verify the error path of handler
        with patch.object(handler, "extract_method_path", side_effect=Exception("Test error")):
            response = handler.lambda_handler(event, {})

    # Verify response structure for error case with HTTP API v2 format
    assert "isAuthorized" in response
    assert response["isAuthorized"] is False


def test_lambda_handler_missing_auth_header(api_gateway_event):
    """Test case with missing Authorization header"""
    event = api_gateway_event.copy()
    event["headers"] = {"Content-Type": "application/json"}  # No Authorization header

    with patch.object(handler.logger, "info"), patch.object(handler.logger, "warning"):
        response = handler.lambda_handler(event, {})

    assert "isAuthorized" in response
    assert response["isAuthorized"] is False


def test_lambda_handler_raw_token(api_gateway_event):
    """Test case with token without 'Bearer ' prefix"""
    event = api_gateway_event.copy()
    event["headers"] = {"Authorization": "raw_token_123", "Content-Type": "application/json"}

    # Mock the verify_token function to return True
    with patch.object(handler, "verify_token", return_value=True):
        with patch.object(handler.logger, "info"):
            response = handler.lambda_handler(event, {})

    assert "isAuthorized" in response
    assert response["isAuthorized"] is True


def test_extract_method_path():
    """Test the extract_method_path function"""
    event = {
        "requestContext": {
            "http": {
                "method": "POST",
                "path": "/search",
                "sourceIp": "192.168.0.1",
                "userAgent": "test-agent",
            }
        }
    }

    http_method, resource_path, source_ip, user_agent = handler.extract_method_path(event)

    assert http_method == "POST"
    assert resource_path == "/search"
    assert source_ip == "192.168.0.1"
    assert user_agent == "test-agent"


def test_verify_token_empty():
    """Test verify_token with empty token"""
    with patch.object(handler.logger, "warning"):
        result = handler.verify_token("")

    assert result is False


def test_verify_token_expired():
    """Test verify_token with expired token"""
    # Direct test of the ExpiredSignatureError exception handling (line 93-95)
    with patch.object(jwt, "get_unverified_header", return_value={"kid": "test-key-id"}):
        with patch.object(jwt, "decode", side_effect=jwt.ExpiredSignatureError("Token expired")):
            with patch.object(handler.logger, "warning") as mock_warning:
                result = handler.verify_token("expired_token")

    # Verify the specific warning message for expired tokens
    mock_warning.assert_called_with("Token has expired")
    assert result is False


def test_verify_token_invalid():
    """Test verify_token with invalid token"""
    # Direct test of the InvalidTokenError exception handling (line 96-98)
    with patch.object(jwt, "get_unverified_header", return_value={"kid": "test-key-id"}):
        with patch.object(jwt, "decode", side_effect=jwt.InvalidTokenError("Invalid token")):
            with patch.object(handler.logger, "warning") as mock_warning:
                result = handler.verify_token("invalid_token")

    # Verify the specific warning message for invalid tokens
    mock_warning.assert_called_with("Invalid token: Invalid token")
    assert result is False


def test_verify_token_unexpected_error():
    """Test verify_token with unexpected error"""
    # Direct test of the generic exception handling (line 99-101)
    with patch.object(jwt, "get_unverified_header", return_value={"kid": "test-key-id"}):
        with patch.object(jwt, "decode", side_effect=Exception("Unexpected error")):
            with patch.object(handler.logger, "error") as mock_error:
                result = handler.verify_token("problematic_token")

    # Verify the specific error message for unexpected errors
    mock_error.assert_called_with("Unexpected error during token verification: Unexpected error")
    assert result is False


def test_verify_token_success():
    """Test verify_token success case"""
    mock_payload = {"iss": handler.ALLOWED_ISSUER, "exp": 1714305458, "iat": 1714219058}

    with patch.object(jwt, "decode", return_value=mock_payload):
        with patch.object(handler.logger, "info"):
            with patch.object(jwt, "get_unverified_header", return_value={"kid": "test-key-id"}):
                result = handler.verify_token("valid-token")

    assert result is True


def test_verify_token_header_parsing_error():
    """Test verify_token with header parsing error"""
    with patch.object(jwt, "get_unverified_header", side_effect=Exception("Header error")):
        with patch.object(handler.logger, "warning"):
            result = handler.verify_token("invalid-header-token")

    assert result is False
