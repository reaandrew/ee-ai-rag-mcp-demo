import json
import unittest
from unittest.mock import patch, MagicMock

import pytest
from src.lambda_functions.auth_authorizer import handler


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
    # Mock logging to avoid interference
    with patch.object(handler.logger, "info"):
        response = handler.lambda_handler(api_gateway_event, {})

    # Verify response structure for HTTP API v2 format
    assert "isAuthorized" in response
    assert response["isAuthorized"] is True


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
