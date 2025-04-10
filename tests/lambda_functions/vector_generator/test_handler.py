import json
import os
import sys
import pytest
from unittest.mock import patch, MagicMock


# Create mocks for opensearchpy imports
class MockOpenSearch:
    def __init__(self, **kwargs):
        self.indices = MagicMock()
        self.indices.exists.return_value = False
        self.indices.create.return_value = {"acknowledged": True}

    def index(self, **kwargs):
        return {"_id": kwargs.get("id", "test_id"), "result": "created"}


class MockRequestsHttpConnection:
    pass


class MockAWS4Auth:
    pass


# Set up module mocks before importing the handler
opensearch_mock = MagicMock()
opensearch_mock.OpenSearch = MockOpenSearch
opensearch_mock.RequestsHttpConnection = MockRequestsHttpConnection

requests_aws4auth_mock = MagicMock()
requests_aws4auth_mock.AWS4Auth = MockAWS4Auth

# Apply the mocks
sys.modules["opensearchpy"] = opensearch_mock
sys.modules["requests_aws4auth"] = requests_aws4auth_mock

# Now we can import the handler module
from src.lambda_functions.vector_generator.handler import (
    lambda_handler,
    generate_embedding,
    process_chunk_file,
    create_index_if_not_exists,
    get_opensearch_credentials,
)


# Sample test data
SAMPLE_CHUNK = {
    "chunk_id": 0,
    "total_chunks": 10,
    "text": "This is a sample text chunk for testing vector generation.",
    "chunk_size": 57,
    "pages": [1],
    "start_page": 1,
    "end_page": 1,
    "document_name": "test-file.txt",
    "page_number": 1,
    "metadata": {
        "source_bucket": "test-bucket",
        "source_key": "test-file.txt",
        "filename": "test-file.txt",
        "content_type": "text/plain",
        "last_modified": "2023-01-01 00:00:00",
        "size_bytes": 1000,
    },
}

SAMPLE_EMBEDDING = [0.1, 0.2, 0.3, 0.4, 0.5]

SAMPLE_S3_EVENT = {
    "Records": [
        {
            "eventSource": "aws:s3",
            "s3": {
                "bucket": {"name": "ee-ai-rag-mcp-demo-chunked-text"},
                "object": {"key": "ee-ai-rag-mcp-demo/test-doc/chunk_0.json"},
            },
        }
    ]
}


@pytest.fixture
def mock_environment():
    """Set up environment variables for testing."""
    os.environ["CHUNKED_TEXT_BUCKET"] = "ee-ai-rag-mcp-demo-chunked-text"
    os.environ["OPENSEARCH_DOMAIN"] = "ee-ai-rag-mcp-demo-vectors"
    os.environ["OPENSEARCH_INDEX"] = "rag-vectors"
    os.environ["VECTOR_PREFIX"] = "ee-ai-rag-mcp-demo"
    os.environ["MODEL_ID"] = "amazon.titan-embed-text-v1"
    os.environ["AWS_REGION"] = "eu-west-2"
    yield
    # Clean up
    os.environ.pop("CHUNKED_TEXT_BUCKET", None)
    os.environ.pop("OPENSEARCH_DOMAIN", None)
    os.environ.pop("OPENSEARCH_INDEX", None)
    os.environ.pop("VECTOR_PREFIX", None)
    os.environ.pop("MODEL_ID", None)
    os.environ.pop("AWS_REGION", None)


class MockResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body


def test_get_opensearch_credentials():
    """Test retrieving credentials from Secrets Manager."""
    mock_response = {"SecretString": json.dumps({"username": "admin", "password": "test-password"})}

    with patch("boto3.client") as mock_boto3:
        mock_secrets_client = MagicMock()
        mock_secrets_client.get_secret_value.return_value = mock_response
        mock_boto3.return_value = mock_secrets_client

        username, password = get_opensearch_credentials()

        # Verify the result
        assert username == "admin"
        assert password == "test-password"

        # Verify that boto3.client was called correctly
        mock_boto3.assert_called_once_with("secretsmanager", region_name="eu-west-2")
        mock_secrets_client.get_secret_value.assert_called_once_with(
            SecretId="ee-ai-rag-mcp-demo/opensearch-master-credentials-v2"
        )


def test_create_index_if_not_exists(mock_environment):
    """Test the create_index_if_not_exists function."""
    # Test index creation when it doesn't exist
    with patch("src.lambda_functions.vector_generator.handler.opensearch_client", MockOpenSearch()):
        result = create_index_if_not_exists()
        assert result is True


def test_generate_embedding():
    """Test the generate_embedding function."""
    with patch("src.lambda_functions.vector_generator.handler.bedrock_runtime") as mock_bedrock:
        # Mock the invoke_model response
        mock_response = {"body": MockResponse(json.dumps({"embedding": SAMPLE_EMBEDDING}).encode())}
        mock_bedrock.invoke_model.return_value = mock_response

        # Call the function
        result = generate_embedding("This is a test text")

        # Assert the result
        assert result == SAMPLE_EMBEDDING

        # Verify that the bedrock client was called correctly
        mock_bedrock.invoke_model.assert_called_once()
        call_args = mock_bedrock.invoke_model.call_args[1]
        # Don't check exact model ID as it varies by environment
        assert "modelId" in call_args
        assert "inputText" in json.loads(call_args["body"])


def test_process_chunk_file(mock_environment):
    """Test the process_chunk_file function."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
        "src.lambda_functions.vector_generator.handler.generate_embedding"
    ) as mock_generate_embedding, patch(
        "src.lambda_functions.vector_generator.handler.opensearch_client"
    ) as mock_opensearch:
        # Mock the S3 get_object response
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(SAMPLE_CHUNK).encode()))
        }

        # Mock the generate_embedding function
        mock_generate_embedding.return_value = SAMPLE_EMBEDDING

        # Mock OpenSearch index method
        mock_opensearch.index.return_value = {"_id": "test_id", "result": "created"}
        mock_opensearch.indices.exists.return_value = True

        # Call the function
        result = process_chunk_file("test-bucket", "test-prefix/chunk_0.json")

        # Assert the result
        assert result["status"] == "success"
        assert result["source"]["bucket"] == "test-bucket"
        assert result["source"]["file_key"] == "test-prefix/chunk_0.json"
        assert result["output"]["opensearch_domain"] == "ee-ai-rag-mcp-demo-vectors"
        assert result["output"]["opensearch_index"] == "rag-vectors"
        assert "document_id" in result["output"]
        assert result["output"]["embedding_dimension"] == len(SAMPLE_EMBEDDING)

        # Verify that OpenSearch index was called
        mock_opensearch.index.assert_called_once()
        call_args = mock_opensearch.index.call_args[1]
        assert call_args["index"] == "rag-vectors"
        assert "body" in call_args
        assert "embedding" in call_args["body"]


def test_lambda_handler(mock_environment):
    """Test the lambda_handler function."""
    with patch("src.lambda_functions.vector_generator.handler.process_chunk_file") as mock_process:
        # Mock the process_chunk_file function to return a success result
        mock_process.return_value = {
            "status": "success",
            "source": {"bucket": "test-bucket", "file_key": "test-key"},
            "output": {
                "opensearch_domain": "ee-ai-rag-mcp-demo-vectors",
                "opensearch_index": "rag-vectors",
                "document_id": "test_id",
                "embedding_dimension": 5,
                "model_id": "amazon.titan-embed-text-v1",
            },
        }

        # Call the function with the sample event
        response = lambda_handler(SAMPLE_S3_EVENT, {})

        # Assert the response
        assert response["statusCode"] == 200
        assert "Processed and vectorized" in response["body"]["message"]
        assert len(response["body"]["results"]) == 1

        # Verify that process_chunk_file was called correctly
        mock_process.assert_called_once_with(
            "ee-ai-rag-mcp-demo-chunked-text", "ee-ai-rag-mcp-demo/test-doc/chunk_0.json"
        )


def test_lambda_handler_skips_non_json(mock_environment):
    """Test that lambda_handler skips non-JSON files."""
    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {"bucket": {"name": "test-bucket"}, "object": {"key": "test-file.txt"}},
            }
        ]
    }

    with patch("src.lambda_functions.vector_generator.handler.process_chunk_file") as mock_process:
        # Call the function
        response = lambda_handler(event, {})

        # Assert that process_chunk_file was not called
        mock_process.assert_not_called()

        # Assert the response
        assert response["statusCode"] == 200
        assert "Processed and vectorized 0" in response["body"]["message"]


def test_lambda_handler_skips_manifest(mock_environment):
    """Test that lambda_handler skips manifest files."""
    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test-doc/manifest.json"},
                },
            }
        ]
    }

    with patch("src.lambda_functions.vector_generator.handler.process_chunk_file") as mock_process:
        # Call the function
        response = lambda_handler(event, {})

        # Assert that process_chunk_file was not called
        mock_process.assert_not_called()

        # Assert the response
        assert response["statusCode"] == 200
        assert "Processed and vectorized 0" in response["body"]["message"]


def test_lambda_handler_handles_error(mock_environment):
    """Test that lambda_handler handles errors gracefully."""
    with patch("src.lambda_functions.vector_generator.handler.process_chunk_file") as mock_process:
        # Mock process_chunk_file to raise an exception
        mock_process.side_effect = Exception("Test error")

        # Call the function
        response = lambda_handler(SAMPLE_S3_EVENT, {})

        # Assert the response
        assert response["statusCode"] == 500
        assert "Error" in response["body"]["message"]
