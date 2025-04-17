import json
import os
import sys
import importlib
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

    def info(self):
        return {"status": "green", "cluster_name": "test-cluster"}


class MockRequestsHttpConnection:
    pass


class MockAWS4Auth:
    pass


# Mock tracking utils
tracking_utils_mock = MagicMock()
tracking_utils_mock.update_indexing_progress.return_value = {
    "status": "success",
    "document_id": "test-doc-id",
    "progress": "1/5",
}

# Set up module mocks before importing the handler
opensearch_mock = MagicMock()
opensearch_mock.OpenSearch = MockOpenSearch
opensearch_mock.RequestsHttpConnection = MockRequestsHttpConnection

requests_aws4auth_mock = MagicMock()
requests_aws4auth_mock.AWS4Auth = MockAWS4Auth

# Mock our utility modules
opensearch_utils_mock = MagicMock()
opensearch_utils_mock.get_opensearch_client.return_value = MockOpenSearch()
opensearch_utils_mock.create_index_if_not_exists.return_value = True

bedrock_utils_mock = MagicMock()
bedrock_utils_mock.generate_embedding.return_value = [0.1, 0.2, 0.3, 0.4, 0.5]

# Apply the mocks
sys.modules["opensearchpy"] = opensearch_mock
sys.modules["requests_aws4auth"] = requests_aws4auth_mock
sys.modules["src.utils.opensearch_utils"] = opensearch_utils_mock
sys.modules["src.utils.bedrock_utils"] = bedrock_utils_mock
sys.modules["src.utils.tracking_utils"] = tracking_utils_mock
sys.modules["utils.tracking_utils"] = tracking_utils_mock

# Now we can import the handler module
from src.lambda_functions.vector_generator.handler import (
    lambda_handler,
    generate_embedding,
    process_chunk_file,
    create_index_if_not_exists,
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


def test_create_index_if_not_exists(mock_environment):
    """Test the create_index_if_not_exists function."""
    # Test that the function calls the utility module correctly
    with patch("src.utils.opensearch_utils.create_index_if_not_exists") as mock_create:
        mock_create.return_value = True

        result = create_index_if_not_exists()
        assert result is True

        # Verify that the utility function was called correctly
        mock_create.assert_called_once()


def test_generate_embedding():
    """Test the generate_embedding function."""
    # Test that the function calls the utility module correctly
    with patch("src.utils.bedrock_utils.generate_embedding") as mock_generate:
        mock_generate.return_value = SAMPLE_EMBEDDING

        # Call the function
        result = generate_embedding("This is a test text")

        # Assert the result
        assert result == SAMPLE_EMBEDDING

        # Verify that the utility function was called correctly
        mock_generate.assert_called_once()
        # Should pass the text and model ID to the utility function
        assert mock_generate.call_args[0][0] == "This is a test text"
        assert "model_id" in mock_generate.call_args[1]


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


def test_lambda_handler_with_empty_event(mock_environment):
    """Test the lambda_handler function with an empty event."""
    # Create an empty event
    empty_event = {}

    # Call the function
    response = lambda_handler(empty_event, {})

    # Assert the response
    assert response["statusCode"] == 200
    assert "Processed and vectorized 0" in response["body"]["message"]
    assert len(response["body"]["results"]) == 0


def test_lambda_handler_with_non_s3_event(mock_environment):
    """Test the lambda_handler function with a non-S3 event."""
    # Create a non-S3 event
    non_s3_event = {"Records": [{"eventSource": "aws:sqs", "other_data": "test"}]}  # Not S3

    with patch("src.lambda_functions.vector_generator.handler.process_chunk_file") as mock_process:
        # Call the function
        response = lambda_handler(non_s3_event, {})

        # Assert that process_chunk_file was not called
        mock_process.assert_not_called()

        # Assert the response
        assert response["statusCode"] == 200
        assert "Processed and vectorized 0" in response["body"]["message"]
        assert len(response["body"]["results"]) == 0


def test_lambda_handler_with_vector_json_file(mock_environment):
    """Test that lambda_handler skips _vector.json files."""
    event = {
        "Records": [
            {
                "eventSource": "aws:s3",
                "s3": {
                    "bucket": {"name": "test-bucket"},
                    "object": {"key": "test-doc/chunk_0_vector.json"},
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


def test_process_chunk_file_with_tracking(mock_environment):
    """Test the process_chunk_file function with document tracking."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
        "src.lambda_functions.vector_generator.handler.opensearch_client"
    ) as mock_opensearch:
        # Mock the S3 get_object response - include a document_id in metadata
        modified_chunk = SAMPLE_CHUNK.copy()
        modified_chunk["metadata"]["document_id"] = "test-doc-id"
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(modified_chunk).encode()))
        }

        # Call the function
        result = process_chunk_file("test-bucket", "test-prefix/chunk_0.json")

        # Verify that tracking_utils.update_indexing_progress was called
        tracking_utils_mock.update_indexing_progress.assert_called_once_with(
            document_id="test-doc-id",
            document_name="test-file.txt",
            page_number="1",
        )

        # Assert the result
        assert result["status"] == "success"


def test_process_chunk_file_without_opensearch_client(mock_environment):
    """Test the process_chunk_file function when OpenSearch client is not available."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
        "src.lambda_functions.vector_generator.handler.opensearch_client", None
    ), patch(
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

        # Assert the result still contains the source info
        assert result["status"] == "success"
        assert result["source"]["bucket"] == "test-bucket"
        assert result["source"]["file_key"] == "test-prefix/chunk_0.json"


def test_process_chunk_file_no_text(mock_environment):
    """Test the process_chunk_file function with a chunk that has no text."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3:
        # Create a chunk with no text
        empty_chunk = SAMPLE_CHUNK.copy()
        empty_chunk["text"] = ""
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(empty_chunk).encode()))
        }

        # Call the function and expect an exception
        with pytest.raises(ValueError, match="No text found in chunk file"):
            process_chunk_file("test-bucket", "test-prefix/empty_chunk.json")


def test_import_failures():
    """Test the behavior when imports fail."""
    # Save the original modules
    original_modules = dict(sys.modules)
    original_opensearch_utils = None
    original_bedrock_utils = None
    original_tracking_utils = None

    # Store original module references if they exist
    if hasattr(
        sys.modules.get("src.lambda_functions.vector_generator.handler", {}), "opensearch_utils"
    ):
        from src.lambda_functions.vector_generator import handler

        original_opensearch_utils = handler.opensearch_utils
        original_bedrock_utils = handler.bedrock_utils
        original_tracking_utils = handler.tracking_utils

    try:
        # Create mocks
        mock_tracking_utils = None

        # Temporarily modify the imported modules
        from src.lambda_functions.vector_generator import handler

        handler.tracking_utils = mock_tracking_utils

        # Test with tracking_utils as None (this simulates import failure)
        assert handler.tracking_utils is None

        # Ensure we can process a chunk file even with tracking_utils as None
        with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
            "src.lambda_functions.vector_generator.handler.opensearch_client"
        ) as mock_opensearch:
            # Mock the S3 response
            modified_chunk = SAMPLE_CHUNK.copy()
            modified_chunk["metadata"]["document_id"] = "test-doc-id"
            mock_s3.get_object.return_value = {
                "Body": MagicMock(read=MagicMock(return_value=json.dumps(modified_chunk).encode()))
            }

            # Call the process_chunk_file function
            result = handler.process_chunk_file("test-bucket", "test-key")

            # Verify it still works without tracking_utils
            assert result["status"] == "success"

    finally:
        # Restore the original modules
        if original_opensearch_utils:
            from src.lambda_functions.vector_generator import handler

            handler.opensearch_utils = original_opensearch_utils
            handler.bedrock_utils = original_bedrock_utils
            handler.tracking_utils = original_tracking_utils


def test_process_chunk_file_with_s3_error(mock_environment):
    """Test the process_chunk_file function when S3 get_object fails."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3:
        # Mock S3 get_object to raise an exception
        mock_s3.get_object.side_effect = Exception("S3 access denied")

        # Call the function and expect the exception to be raised
        with pytest.raises(Exception, match="S3 access denied"):
            process_chunk_file("test-bucket", "test-prefix/chunk_0.json")


def test_process_chunk_file_with_opensearch_error(mock_environment):
    """Test process_chunk_file when OpenSearch indexing fails."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
        "src.lambda_functions.vector_generator.handler.opensearch_client"
    ) as mock_opensearch:
        # Mock the S3 get_object response
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(SAMPLE_CHUNK).encode()))
        }

        # Mock OpenSearch index method to raise an exception
        mock_opensearch.index.side_effect = Exception("OpenSearch indexing error")

        # Call the function and expect the exception to propagate
        with pytest.raises(Exception, match="OpenSearch indexing error"):
            process_chunk_file("test-bucket", "test-prefix/chunk_0.json")


def test_process_chunk_file_with_embedding_error(mock_environment):
    """Test process_chunk_file when embedding generation fails."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
        "src.lambda_functions.vector_generator.handler.generate_embedding"
    ) as mock_generate_embedding:
        # Mock the S3 get_object response
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(SAMPLE_CHUNK).encode()))
        }

        # Mock the generate_embedding function to raise an exception
        mock_generate_embedding.side_effect = Exception("Embedding generation failed")

        # Call the function and expect the exception to propagate
        with pytest.raises(Exception, match="Embedding generation failed"):
            process_chunk_file("test-bucket", "test-prefix/chunk_0.json")


def test_process_chunk_file_with_tracking_none(mock_environment):
    """Test process_chunk_file when tracking_utils is None."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
        "src.lambda_functions.vector_generator.handler.opensearch_client"
    ) as mock_opensearch, patch(
        "src.lambda_functions.vector_generator.handler.tracking_utils", None
    ):
        # Mock the S3 get_object response - include a document_id in metadata
        modified_chunk = SAMPLE_CHUNK.copy()
        modified_chunk["metadata"]["document_id"] = "test-doc-id"
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(modified_chunk).encode()))
        }

        # Call the function
        result = process_chunk_file("test-bucket", "test-prefix/chunk_0.json")

        # Assert the result is still success
        assert result["status"] == "success"


def test_process_chunk_file_with_tracking_error(mock_environment):
    """Test process_chunk_file when tracking_utils.update_indexing_progress raises an exception."""
    with patch("src.lambda_functions.vector_generator.handler.s3_client") as mock_s3, patch(
        "src.lambda_functions.vector_generator.handler.opensearch_client"
    ) as mock_opensearch, patch(
        "src.lambda_functions.vector_generator.handler.tracking_utils"
    ) as mock_tracking:
        # Mock the S3 get_object response - include a document_id in metadata
        modified_chunk = SAMPLE_CHUNK.copy()
        modified_chunk["metadata"]["document_id"] = "test-doc-id"
        mock_s3.get_object.return_value = {
            "Body": MagicMock(read=MagicMock(return_value=json.dumps(modified_chunk).encode()))
        }

        # Mock tracking_utils.update_indexing_progress to raise an exception
        mock_tracking.update_indexing_progress.side_effect = Exception("Tracking error")

        # The current implementation propagates the error, so we expect an exception
        with pytest.raises(Exception, match="Tracking error"):
            process_chunk_file("test-bucket", "test-prefix/chunk_0.json")
