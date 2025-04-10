import json
import os
import unittest
from unittest.mock import patch, MagicMock

import pytest
from src.lambda_functions.policy_search import handler


@pytest.fixture
def mock_env_variables(monkeypatch):
    """Set up mock environment variables for tests"""
    monkeypatch.setenv("OPENSEARCH_DOMAIN", "test-opensearch-domain")
    monkeypatch.setenv("OPENSEARCH_INDEX", "test-index")
    monkeypatch.setenv("EMBEDDING_MODEL_ID", "test-embedding-model")
    monkeypatch.setenv("LLM_MODEL_ID", "test-llm-model")


@pytest.fixture
def api_gateway_event():
    """Create a sample API Gateway event"""
    return {
        "body": json.dumps({"query": "What is our password policy?"}),
        "resource": "/search",
        "path": "/search",
        "httpMethod": "POST",
        "headers": {
            "Content-Type": "application/json",
        },
        "requestContext": {
            "resourcePath": "/search",
            "httpMethod": "POST",
        },
    }


@pytest.fixture
def mock_opensearch_response():
    """Create a sample OpenSearch response"""
    return {
        "hits": {
            "total": {"value": 2},
            "hits": [
                {
                    "_score": 0.95,
                    "_source": {
                        "text": "Passwords must be at least 12 characters long.",
                        "document_name": "Password Policy",
                        "page_number": 1,
                        "metadata": {"section": "Requirements"},
                    },
                },
                {
                    "_score": 0.85,
                    "_source": {
                        "text": "Passwords must be changed every 90 days.",
                        "document_name": "Password Policy",
                        "page_number": 2,
                        "metadata": {"section": "Management"},
                    },
                },
            ],
        }
    }


@pytest.fixture
def mock_bedrock_embedding_response():
    """Create a sample Bedrock Titan embedding response"""
    return {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps({"embedding": [0.1, 0.2, 0.3, 0.4, 0.5] * 10}).encode()
            )
        )
    }


@pytest.fixture
def mock_bedrock_llm_response():
    """Create a sample Bedrock Claude response"""
    return {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(
                    {
                        "content": [
                            {
                                "text": "Based on the provided policy excerpts, passwords must be at least 12 characters long (Password Policy, Page 1) and must be changed every 90 days (Password Policy, Page 2)."
                            }
                        ]
                    }
                ).encode()
            )
        )
    }


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_extract_query_from_event(mock_bedrock, mock_opensearch, api_gateway_event):
    """Test extracting query from API Gateway event"""
    query = handler.extract_query_from_event(api_gateway_event)
    assert query == "What is our password policy?"


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_extract_query_missing_query(mock_bedrock, mock_opensearch):
    """Test extracting query when it's missing"""
    event = {"body": json.dumps({"not_query": "test"})}
    with pytest.raises(ValueError):
        handler.extract_query_from_event(event)


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_generate_embedding(mock_bedrock, mock_opensearch, mock_bedrock_embedding_response):
    """Test generating embeddings with Bedrock"""
    mock_bedrock.invoke_model.return_value = mock_bedrock_embedding_response

    embedding = handler.generate_embedding("test query")

    assert len(embedding) == 50  # 5*10 from our mock
    mock_bedrock.invoke_model.assert_called_once()


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_search_opensearch(mock_bedrock, mock_opensearch, mock_opensearch_response):
    """Test searching OpenSearch"""
    mock_opensearch.search.return_value = mock_opensearch_response

    results = handler.search_opensearch([0.1, 0.2, 0.3], top_k=2)

    assert len(results) == 2
    assert results[0]["document_name"] == "Password Policy"
    assert results[0]["page_number"] == 1
    mock_opensearch.search.assert_called_once()


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_lambda_handler_successful(
    mock_bedrock,
    mock_opensearch,
    api_gateway_event,
    mock_opensearch_response,
    mock_bedrock_embedding_response,
    mock_bedrock_llm_response,
):
    """Test successful lambda_handler execution"""
    # Set up mocks
    mock_bedrock.invoke_model.side_effect = [
        mock_bedrock_embedding_response,  # For embedding generation
        mock_bedrock_llm_response,  # For LLM response
    ]
    mock_opensearch.search.return_value = mock_opensearch_response

    # Execute Lambda handler
    response = handler.lambda_handler(api_gateway_event, {})

    # Verify response
    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    assert "answer" in response_body
    assert "sources" in response_body
    assert len(response_body["sources"]) > 0


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_format_results_for_prompt(mock_bedrock, mock_opensearch, mock_opensearch_response):
    """Test formatting search results for prompt"""
    # Get search results
    mock_opensearch.search.return_value = mock_opensearch_response
    search_results = handler.search_opensearch(query_embedding=[0.1, 0.2, 0.3])

    # Test formatting
    formatted = handler.format_results_for_prompt(search_results)

    assert "Password Policy" in formatted
    assert "Page 1" in formatted
    assert "Page 2" in formatted


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_extract_sources(mock_bedrock, mock_opensearch, mock_opensearch_response):
    """Test extracting sources from search results"""
    # Get search results
    mock_opensearch.search.return_value = mock_opensearch_response
    search_results = handler.search_opensearch(query_embedding=[0.1, 0.2, 0.3])

    # Test source extraction
    sources = handler.extract_sources(search_results)

    assert len(sources) == 2  # Two results from same document but different pages
    assert sources[0]["document_name"] == "Password Policy"
    assert "page_number" in sources[0]


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_create_claude_prompt(mock_bedrock, mock_opensearch):
    """Test creating prompt for Claude"""
    query = "What is the password policy?"
    formatted_results = "Document 1: Test doc, Page 5\nSome text here"

    prompt = handler.create_claude_prompt(query, formatted_results)

    assert "anthropic_version" in prompt
    assert "system" in prompt
    assert "messages" in prompt
    assert len(prompt["messages"]) == 1
    assert prompt["messages"][0]["role"] == "user"
    assert query in prompt["messages"][0]["content"]


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_lambda_handler_error(mock_bedrock, mock_opensearch):
    """Test error handling in lambda_handler"""
    # Create event with invalid body
    event = {"body": '{"not_a_query": "test"}'}

    # Execute Lambda handler
    response = handler.lambda_handler(event, {})

    # Verify error response
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "error" in response_body


@patch.object(handler, "opensearch_client", None)  # Set client to None
@patch.object(handler, "bedrock_runtime")
def test_search_opensearch_no_client(mock_bedrock):
    """Test search_opensearch when OpenSearch client is not available"""
    with pytest.raises(ValueError, match="OpenSearch client not available"):
        handler.search_opensearch(query_embedding=[0.1, 0.2, 0.3])


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_search_opensearch_error(mock_bedrock, mock_opensearch):
    """Test search_opensearch when an error occurs"""
    # Mock an error in OpenSearch search
    mock_opensearch.search.side_effect = Exception("Search error")

    with pytest.raises(Exception, match="Search error"):
        handler.search_opensearch(query_embedding=[0.1, 0.2, 0.3])


@patch.object(handler, "bedrock_runtime")
def test_generate_embedding_error(mock_bedrock):
    """Test generate_embedding when an error occurs"""
    # Mock an error in Bedrock invoke_model
    mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")

    with pytest.raises(Exception, match="Bedrock error"):
        handler.generate_embedding(text="test query")


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_generate_llm_response_completion_format(mock_bedrock, mock_opensearch):
    """Test generate_llm_response with an older completion format"""
    # Mock response with older completion format
    response = {
        "body": MagicMock(
            read=MagicMock(
                return_value=json.dumps(
                    {"completion": "This is a test response in the older format."}
                ).encode()
            )
        )
    }
    mock_bedrock.invoke_model.return_value = response

    # Test the function
    result = handler.generate_llm_response({"prompt": "test"})

    # Verify the result
    assert result == "This is a test response in the older format."


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_generate_llm_response_error(mock_bedrock, mock_opensearch):
    """Test generate_llm_response when an error occurs"""
    # Mock an error in Bedrock invoke_model
    mock_bedrock.invoke_model.side_effect = Exception("Bedrock error")

    with pytest.raises(Exception, match="Bedrock error"):
        handler.generate_llm_response({"prompt": "test"})


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_lambda_handler_system_error(mock_bedrock, mock_opensearch, api_gateway_event):
    """Test lambda_handler when a system error occurs"""
    # Mock an error in search_opensearch
    mock_bedrock.invoke_model.side_effect = Exception("System error")

    # Execute Lambda handler
    response = handler.lambda_handler(api_gateway_event, {})

    # Verify error response
    assert response["statusCode"] == 500
    response_body = json.loads(response["body"])
    assert "error" in response_body


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_extract_query_invalid_json(mock_bedrock, mock_opensearch):
    """Test extract_query_from_event with invalid JSON"""
    event = {"body": "invalid json"}

    with pytest.raises(ValueError, match="Invalid JSON in request body"):
        handler.extract_query_from_event(event)


@patch.object(handler, "opensearch_client")
@patch.object(handler, "bedrock_runtime")
def test_extract_query_no_body(mock_bedrock, mock_opensearch):
    """Test extract_query_from_event with no body"""
    event = {"not_body": "value"}

    with pytest.raises(ValueError, match="Invalid request format"):
        handler.extract_query_from_event(event)


def test_get_opensearch_credentials():
    """Test get_opensearch_credentials function"""
    with patch("boto3.client") as mock_client:
        # Mock successful response
        mock_secrets_manager = MagicMock()
        mock_client.return_value = mock_secrets_manager
        mock_secrets_manager.get_secret_value.return_value = {
            "SecretString": json.dumps({"username": "test_user", "password": "test_pass"})
        }

        # Test the function
        username, password = handler.get_opensearch_credentials()

        # Verify the result
        assert username == "test_user"
        assert password == "test_pass"

        # Test with error
        mock_secrets_manager.get_secret_value.side_effect = Exception("Secret error")

        # Should return None, None when there's an error
        username, password = handler.get_opensearch_credentials()
        assert username is None
        assert password is None


@patch("boto3.Session")
def test_get_opensearch_client_no_credentials(mock_session):
    """Test get_opensearch_client when no credentials are available"""
    mock_session.return_value.get_credentials.return_value = None

    # Mock the logging to avoid interference
    with patch.object(handler.logger, "warning"):
        client = handler.get_opensearch_client()

    # Should return None when no credentials are available
    assert client is None
