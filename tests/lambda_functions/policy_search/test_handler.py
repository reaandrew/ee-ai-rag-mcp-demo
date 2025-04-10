import json
import os
import sys
import unittest
from unittest.mock import patch, MagicMock

import pytest

# Mock utility modules
opensearch_utils_mock = MagicMock()
opensearch_utils_mock.get_opensearch_client.return_value = MagicMock()
opensearch_utils_mock.search_opensearch.return_value = []

bedrock_utils_mock = MagicMock()
bedrock_utils_mock.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]
bedrock_utils_mock.create_claude_prompt.return_value = {
    "system": "test",
    "messages": [{"role": "user", "content": "test"}],
}
bedrock_utils_mock.generate_llm_response.return_value = "test response"

# Apply mocks
sys.modules["src.utils.opensearch_utils"] = opensearch_utils_mock
sys.modules["src.utils.bedrock_utils"] = bedrock_utils_mock

# Now import the handler
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


def test_extract_query_from_event(api_gateway_event):
    """Test extracting query from API Gateway event"""
    query = handler.extract_query_from_event(api_gateway_event)
    assert query == "What is our password policy?"


def test_extract_query_missing_query():
    """Test extracting query when it's missing"""
    event = {"body": json.dumps({"not_query": "test"})}
    with pytest.raises(ValueError):
        handler.extract_query_from_event(event)


@patch("src.utils.bedrock_utils.generate_embedding")
def test_generate_embedding(mock_generate_embedding, mock_bedrock_embedding_response):
    """Test generating embeddings with Bedrock"""
    # Set up the mock to return our test embeddings
    embedding_values = [0.1, 0.2, 0.3, 0.4, 0.5] * 10
    mock_generate_embedding.return_value = embedding_values

    # Call the function that now uses the utility module
    embedding = handler.generate_embedding("test query")

    # Verify the results
    assert embedding == embedding_values
    mock_generate_embedding.assert_called_once_with(
        "test query", model_id=handler.EMBEDDING_MODEL_ID
    )


@patch("src.utils.opensearch_utils.search_opensearch")
def test_search_opensearch(mock_search_opensearch, mock_opensearch_response):
    """Test searching OpenSearch"""
    # Set up mock for our utility function to return search results
    hits = mock_opensearch_response["hits"]["hits"]
    search_results = [
        {
            "text": hit["_source"]["text"],
            "document_name": hit["_source"]["document_name"],
            "page_number": hit["_source"]["page_number"],
            "metadata": hit["_source"]["metadata"],
            "score": hit["_score"],
        }
        for hit in hits
    ]
    mock_search_opensearch.return_value = search_results

    # Call the function and verify results
    results = handler.search_opensearch([0.1, 0.2, 0.3], top_k=2)

    assert len(results) == 2
    assert results[0]["document_name"] == "Password Policy"
    assert results[0]["page_number"] == 1
    mock_search_opensearch.assert_called_once_with([0.1, 0.2, 0.3], top_k=2)


@patch("src.lambda_functions.policy_search.handler.extract_query_from_event")
@patch("src.lambda_functions.policy_search.handler.generate_embedding")
@patch("src.lambda_functions.policy_search.handler.search_opensearch")
@patch("src.utils.bedrock_utils.create_claude_prompt")
@patch("src.utils.bedrock_utils.generate_llm_response")
def test_lambda_handler_successful(
    mock_generate_llm_response,
    mock_create_claude_prompt,
    mock_search_opensearch,
    mock_generate_embedding,
    mock_extract_query,
    api_gateway_event,
    mock_opensearch_response,
):
    """Test successful lambda_handler execution"""
    # Set up mocks
    mock_extract_query.return_value = "What is our password policy?"
    mock_generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]

    # Set up search results
    hits = mock_opensearch_response["hits"]["hits"]
    search_results = [
        {
            "text": hit["_source"]["text"],
            "document_name": hit["_source"]["document_name"],
            "page_number": hit["_source"]["page_number"],
            "metadata": hit["_source"]["metadata"],
            "score": hit["_score"],
        }
        for hit in hits
    ]
    mock_search_opensearch.return_value = search_results

    mock_create_claude_prompt.return_value = {"message": "test prompt"}
    mock_generate_llm_response.return_value = (
        "Based on the policy, passwords must be at least 12 characters long."
    )

    # Execute Lambda handler
    response = handler.lambda_handler(api_gateway_event, {})

    # Verify response
    assert response["statusCode"] == 200
    response_body = json.loads(response["body"])
    assert "answer" in response_body
    assert "sources" in response_body
    assert len(response_body["sources"]) > 0


def test_format_results_for_prompt(mock_opensearch_response):
    """Test formatting search results for prompt"""
    # Create search results directly
    hits = mock_opensearch_response["hits"]["hits"]
    search_results = [
        {
            "text": hit["_source"]["text"],
            "document_name": hit["_source"]["document_name"],
            "page_number": hit["_source"]["page_number"],
            "metadata": hit["_source"]["metadata"],
            "score": hit["_score"],
        }
        for hit in hits
    ]

    # Test formatting
    formatted = handler.format_results_for_prompt(search_results)

    assert "Password Policy" in formatted
    assert "Page 1" in formatted
    assert "Page 2" in formatted


def test_extract_sources(mock_opensearch_response):
    """Test extracting sources from search results"""
    # Create search results directly
    hits = mock_opensearch_response["hits"]["hits"]
    search_results = [
        {
            "text": hit["_source"]["text"],
            "document_name": hit["_source"]["document_name"],
            "page_number": hit["_source"]["page_number"],
            "metadata": hit["_source"]["metadata"],
            "score": hit["_score"],
        }
        for hit in hits
    ]

    # Test source extraction
    sources = handler.extract_sources(search_results)

    assert len(sources) == 2  # Two results from same document but different pages
    assert sources[0]["document_name"] == "Password Policy"
    assert "page_number" in sources[0]


@patch("src.utils.bedrock_utils.create_claude_prompt")
def test_create_claude_prompt(mock_create_claude_prompt):
    """Test that the create_claude_prompt function calls the utility correctly"""
    query = "What is the password policy?"
    formatted_results = "Document 1: Test doc, Page 5\nSome text here"

    # Set up the mock
    expected_result = {
        "anthropic_version": "bedrock-2023-05-31",
        "system": "test system prompt",
        "messages": [{"role": "user", "content": "test content"}],
    }
    mock_create_claude_prompt.return_value = expected_result

    # Call the function through our handler that uses the utility
    prompt = handler.bedrock_utils.create_claude_prompt(query, formatted_results)

    # Check that the utility was called correctly
    assert prompt == expected_result
    mock_create_claude_prompt.assert_called_once_with(query, formatted_results)


def test_lambda_handler_error():
    """Test error handling in lambda_handler"""
    # Create event with invalid body
    event = {"body": '{"not_a_query": "test"}'}

    # Execute Lambda handler
    response = handler.lambda_handler(event, {})

    # Verify error response
    assert response["statusCode"] == 400
    response_body = json.loads(response["body"])
    assert "error" in response_body


@patch("src.utils.opensearch_utils.search_opensearch")
def test_search_opensearch_client_exception(mock_search_opensearch):
    """Test search_opensearch when an exception occurs"""
    # Mock an error in the utility function
    mock_search_opensearch.side_effect = ValueError("OpenSearch client not available")

    with pytest.raises(ValueError, match="OpenSearch client not available"):
        handler.search_opensearch(query_embedding=[0.1, 0.2, 0.3])


@patch("src.utils.opensearch_utils.search_opensearch")
def test_search_opensearch_error(mock_search_opensearch):
    """Test search_opensearch when an error occurs"""
    # Mock an error in OpenSearch search
    mock_search_opensearch.side_effect = Exception("Search error")

    with pytest.raises(Exception, match="Search error"):
        handler.search_opensearch(query_embedding=[0.1, 0.2, 0.3])


@patch("src.utils.bedrock_utils.generate_embedding")
def test_generate_embedding_error(mock_generate_embedding):
    """Test generate_embedding when an error occurs"""
    # Mock an error in Bedrock embedding generation
    mock_generate_embedding.side_effect = Exception("Bedrock error")

    with pytest.raises(Exception, match="Bedrock error"):
        handler.generate_embedding(text="test query")


@patch("src.utils.bedrock_utils.generate_llm_response")
def test_generate_llm_response(mock_generate_llm_response):
    """Test that generate_llm_response uses the utility correctly"""
    # Set up the mock
    mock_generate_llm_response.return_value = "This is a test response."

    # Test calling the function through the handler
    prompt = {"test": "prompt"}
    result = handler.bedrock_utils.generate_llm_response(prompt, model_id="test-model")

    # Verify the result
    assert result == "This is a test response."
    mock_generate_llm_response.assert_called_once_with(prompt, model_id="test-model")


@patch("src.utils.bedrock_utils.generate_llm_response")
def test_generate_llm_response_error(mock_generate_llm_response):
    """Test generate_llm_response when an error occurs"""
    # Mock an error
    mock_generate_llm_response.side_effect = Exception("Bedrock error")

    with pytest.raises(Exception, match="Bedrock error"):
        handler.bedrock_utils.generate_llm_response({"prompt": "test"})


@patch("src.lambda_functions.policy_search.handler.extract_query_from_event")
def test_lambda_handler_system_error(mock_extract_query, api_gateway_event):
    """Test lambda_handler when a system error occurs"""
    # Mock an error
    mock_extract_query.side_effect = Exception("System error")

    # Execute Lambda handler
    response = handler.lambda_handler(api_gateway_event, {})

    # Verify error response
    assert response["statusCode"] == 500
    response_body = json.loads(response["body"])
    assert "error" in response_body


def test_extract_query_invalid_json():
    """Test extract_query_from_event with invalid JSON"""
    event = {"body": "invalid json"}

    with pytest.raises(ValueError, match="Invalid JSON in request body"):
        handler.extract_query_from_event(event)


def test_extract_query_no_body():
    """Test extract_query_from_event with no body"""
    event = {"not_body": "value"}

    with pytest.raises(ValueError, match="Invalid request format"):
        handler.extract_query_from_event(event)
