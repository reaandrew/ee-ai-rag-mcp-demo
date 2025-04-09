import json
import os
import pytest
from unittest.mock import patch, MagicMock, mock_open

# Import the handler module
from src.lambda_functions.vector_generator.handler import (
    lambda_handler,
    generate_embedding,
    process_chunk_file,
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
    "metadata": {
        "source_bucket": "test-bucket",
        "source_key": "test-file.txt",
        "filename": "test-file.txt",
        "content_type": "text/plain",
        "last_modified": "2023-01-01 00:00:00",
        "size_bytes": 1000,
        "pages": [1],
        "start_page": 1,
        "end_page": 1,
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
    os.environ["VECTOR_BUCKET"] = "ee-ai-rag-mcp-demo-vectors"
    os.environ["VECTOR_PREFIX"] = "ee-ai-rag-mcp-demo"
    os.environ["MODEL_ID"] = "amazon.titan-embed-text-v1"
    yield
    # Clean up
    os.environ.pop("CHUNKED_TEXT_BUCKET", None)
    os.environ.pop("VECTOR_BUCKET", None)
    os.environ.pop("VECTOR_PREFIX", None)
    os.environ.pop("MODEL_ID", None)


class MockResponse:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body


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
        assert call_args["modelId"] == "amazon.titan-embed-text-v1"
        assert "inputText" in json.loads(call_args["body"])


def test_process_chunk_file(mock_environment):
    """Test the process_chunk_file function."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
        "src.lambda_functions.vector_generator.handler.generate_embedding"
    ) as mock_generate_embedding:
        # Mock the S3 get_object response
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(SAMPLE_CHUNK).encode()))
        }

        # Mock the generate_embedding function
        mock_generate_embedding.return_value = SAMPLE_EMBEDDING

        # Call the function
        result = process_chunk_file("test-bucket", "test-prefix/chunk_0.json")

        # Assert the result
        assert result["status"] == "success"
        assert result["source"]["bucket"] == "test-bucket"
        assert result["source"]["file_key"] == "test-prefix/chunk_0.json"
        assert result["output"]["bucket"] == "ee-ai-rag-mcp-demo-vectors"
        assert "vector_key" in result["output"]
        assert result["output"]["embedding_dimension"] == len(SAMPLE_EMBEDDING)

        # Verify that S3 put_object was called correctly
        mock_s3.put_object.assert_called_once()
        call_args = mock_s3.put_object.call_args[1]
        assert call_args["Bucket"] == "ee-ai-rag-mcp-demo-vectors"
        assert "Body" in call_args
        assert "embedding" in json.loads(call_args["Body"])


def test_lambda_handler(mock_environment):
    """Test the lambda_handler function."""
    with patch("src.lambda_functions.vector_generator.handler.process_chunk_file") as mock_process:
        # Mock the process_chunk_file function to return a success result
        mock_process.return_value = {
            "status": "success",
            "source": {"bucket": "test-bucket", "file_key": "test-key"},
            "output": {"bucket": "test-vector-bucket", "vector_key": "test-vector-key"},
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
