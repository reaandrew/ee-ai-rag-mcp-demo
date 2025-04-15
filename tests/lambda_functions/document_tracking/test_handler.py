import json
import pytest
import decimal
import sys
from unittest.mock import MagicMock, patch

# Create a mock for boto3 and dynamodb
boto3_mock = MagicMock()
dynamodb_mock = MagicMock()
table_mock = MagicMock()
boto3_mock.resource.return_value = dynamodb_mock
dynamodb_mock.Table.return_value = table_mock

# Apply the boto3 mock
sys.modules["boto3"] = boto3_mock

# Now import the handler module
try:
    from src.lambda_functions.document_tracking.handler import (
        lambda_handler,
        initialize_document_tracking,
        update_indexing_progress,
        complete_document_indexing,
        get_document_history,
        DecimalEncoder,
    )
except ImportError:
    from lambda_functions.document_tracking.handler import (
        lambda_handler,
        initialize_document_tracking,
        update_indexing_progress,
        complete_document_indexing,
        get_document_history,
        DecimalEncoder,
    )


@pytest.fixture
def document_processing_started_event():
    """Create a test SNS event for document processing started"""
    return {
        "Records": [
            {
                "Sns": {
                    "Subject": "Document Processing Started",
                    "Message": json.dumps(
                        {
                            "document_id": "test-bucket/test-document/v123456789",
                            "base_document_id": "test-bucket/test-document",
                            "document_name": "test-document.pdf",
                            "document_version": "v123456789",
                            "upload_timestamp": 123456789,
                            "total_chunks": 5,
                            "status": "PROCESSING",
                            "start_time": "2023-01-01T00:00:00",
                            "is_reupload": False,
                        }
                    ),
                },
            }
        ]
    }


@pytest.fixture
def document_chunk_indexed_event():
    """Create a test SNS event for document chunk indexed"""
    return {
        "Records": [
            {
                "Sns": {
                    "Subject": "Document Chunk Indexed",
                    "Message": json.dumps(
                        {
                            "document_id": "test-bucket/test-document/v123456789",
                            "base_document_id": "test-bucket/test-document",
                            "document_name": "test-document.pdf",
                            "page_number": "1",
                            "document_version": "v123456789",
                            "progress": "1/5",
                            "current_chunks": 0,
                            "total_chunks": 5,
                            "status": "indexed",
                            "timestamp": "2023-01-01T00:01:00",
                        }
                    ),
                },
            }
        ]
    }


@pytest.fixture
def document_indexing_completed_event():
    """Create a test SNS event for document indexing completed"""
    return {
        "Records": [
            {
                "Sns": {
                    "Subject": "Document Indexing Completed",
                    "Message": json.dumps(
                        {
                            "document_id": "test-bucket/test-document/v123456789",
                            "base_document_id": "test-bucket/test-document",
                            "document_name": "test-document.pdf",
                            "document_version": "v123456789",
                            "upload_timestamp": 123456789,
                            "total_chunks": 5,
                            "status": "COMPLETED",
                            "completion_time": "2023-01-01T00:05:00",
                        }
                    ),
                },
            }
        ]
    }


def test_decimal_encoder():
    """Test the DecimalEncoder class with various input types"""
    encoder = DecimalEncoder()

    # Test with integer decimal
    assert encoder.default(decimal.Decimal("5")) == 5

    # Test with floating point decimal
    assert encoder.default(decimal.Decimal("5.5")) == 5.5

    # Test with non-decimal value
    with pytest.raises(TypeError):
        encoder.default("test")


def test_initialize_document_tracking_new_document():
    """Test initializing tracking for a completely new document"""
    # Reset mocks
    table_mock.reset_mock()

    # Mock get_document_history
    with patch(
        "src.lambda_functions.document_tracking.handler.get_document_history", return_value=[]
    ):
        # Test data
        message_data = {
            "document_id": "test-bucket/test-document/v123456789",
            "base_document_id": "test-bucket/test-document",
            "document_name": "test-document.pdf",
            "document_version": "v123456789",
            "upload_timestamp": 123456789,
            "total_chunks": 5,
            "status": "PROCESSING",
            "start_time": "2023-01-01T00:00:00",
            "is_reupload": False,
        }

        # Initialize tracking
        result = initialize_document_tracking(message_data)

        # Assertions
        assert result is True
        table_mock.put_item.assert_called_once()
        # Verify no existing documents were canceled
        assert "UPDATE" not in str(table_mock.mock_calls)


def test_initialize_document_tracking_reupload():
    """Test initializing tracking for a document reupload with existing processing version"""
    # Reset mocks
    table_mock.reset_mock()

    # Mock existing processing document
    existing_doc = {"document_id": "test-bucket/test-document/v123456780", "status": "PROCESSING"}

    # Mock get_document_history
    with patch(
        "src.lambda_functions.document_tracking.handler.get_document_history",
        return_value=[existing_doc],
    ):
        # Test data
        message_data = {
            "document_id": "test-bucket/test-document/v123456789",
            "base_document_id": "test-bucket/test-document",
            "document_name": "test-document.pdf",
            "document_version": "v123456789",
            "upload_timestamp": 123456789,
            "total_chunks": 5,
            "status": "PROCESSING",
            "start_time": "2023-01-01T00:00:00",
            "is_reupload": True,
        }

        # Initialize tracking
        result = initialize_document_tracking(message_data)

        # Assertions
        assert result is True
        table_mock.put_item.assert_called_once()
        # Verify existing document was canceled
        table_mock.update_item.assert_called_once()


def test_initialize_document_tracking_error():
    """Test error handling in initialize_document_tracking"""
    # Reset mocks
    table_mock.reset_mock()

    # Configure mock to raise exception
    table_mock.put_item.side_effect = Exception("Test exception")

    # Test data
    message_data = {
        "document_id": "test-bucket/test-document/v123456789",
        "base_document_id": "test-bucket/test-document",
        "document_name": "test-document.pdf",
    }

    # Should return False on exception
    result = initialize_document_tracking(message_data)

    # Assertions
    assert result is False

    # Reset side_effect for other tests
    table_mock.put_item.side_effect = None


def test_update_indexing_progress_with_progress():
    """Test updating indexing progress with a progress value"""
    # Reset mocks
    table_mock.reset_mock()

    # Mock document response
    table_mock.get_item.return_value = {
        "Item": {
            "document_id": "test-bucket/test-document/v123456789",
            "total_chunks": 5,
            "indexed_chunks": 2,
        }
    }

    # Test data with progress field
    message_data = {
        "document_id": "test-bucket/test-document/v123456789",
        "document_name": "test-document.pdf",
        "progress": "4/5",
    }

    # Update progress
    result = update_indexing_progress(message_data)

    # Assertions
    assert result is True
    table_mock.get_item.assert_called_once()
    table_mock.update_item.assert_called_once()


def test_update_indexing_progress_increment():
    """Test incrementing indexing progress without a progress value"""
    # Reset mocks
    table_mock.reset_mock()

    # Mock document response
    table_mock.get_item.return_value = {
        "Item": {
            "document_id": "test-bucket/test-document/v123456789",
            "total_chunks": 5,
            "indexed_chunks": 2,
        }
    }

    # Mock update response
    table_mock.update_item.return_value = {
        "Attributes": {
            "indexed_chunks": 3,
        }
    }

    # Test data without progress field
    message_data = {
        "document_id": "test-bucket/test-document/v123456789",
        "document_name": "test-document.pdf",
    }

    # Update progress
    result = update_indexing_progress(message_data)

    # Assertions
    assert result is True
    table_mock.get_item.assert_called_once()
    table_mock.update_item.assert_called_once()


def test_update_indexing_progress_conditional_exception():
    """Test conditional exception during increment"""
    # Reset mocks
    table_mock.reset_mock()

    # Mock document response
    table_mock.get_item.return_value = {
        "Item": {
            "document_id": "test-bucket/test-document/v123456789",
            "total_chunks": 5,
            "indexed_chunks": 5,  # Already at maximum
        }
    }

    # Set up update_item to raise ConditionalCheckFailedException
    class ConditionalCheckFailedException(Exception):
        pass

    # Create the mock exception structure
    dynamodb_mock.meta.client.exceptions.ConditionalCheckFailedException = (
        ConditionalCheckFailedException
    )
    table_mock.meta.client.exceptions.ConditionalCheckFailedException = (
        ConditionalCheckFailedException
    )

    # Configure mock to raise exception
    table_mock.update_item.side_effect = ConditionalCheckFailedException()

    # Test data without progress field
    message_data = {
        "document_id": "test-bucket/test-document/v123456789",
        "document_name": "test-document.pdf",
    }

    # Update progress - should still return True despite the exception
    result = update_indexing_progress(message_data)

    # Assertions
    assert result is True
    table_mock.get_item.assert_called_once()
    table_mock.update_item.assert_called_once()

    # Reset side_effect for other tests
    table_mock.update_item.side_effect = None


def test_update_indexing_progress_no_document_id():
    """Test update with no document_id"""
    # Reset mocks
    table_mock.reset_mock()

    # Test data with missing document_id
    message_data = {
        "document_name": "test-document.pdf",
        "progress": "4/5",
    }

    # Should return False when document_id is missing
    result = update_indexing_progress(message_data)

    # Assertions
    assert result is False
    table_mock.get_item.assert_not_called()


def test_update_indexing_progress_error():
    """Test error handling in update_indexing_progress"""
    # Reset mocks
    table_mock.reset_mock()

    # Configure mock to raise exception
    table_mock.get_item.side_effect = Exception("Test exception")

    # Test data
    message_data = {
        "document_id": "test-bucket/test-document/v123456789",
        "document_name": "test-document.pdf",
    }

    # Should return False on exception
    result = update_indexing_progress(message_data)

    # Assertions
    assert result is False

    # Reset side_effect for other tests
    table_mock.get_item.side_effect = None


def test_complete_document_indexing_success():
    """Test marking document as complete"""
    # Reset mocks
    table_mock.reset_mock()

    # Test data
    message_data = {
        "document_id": "test-bucket/test-document/v123456789",
        "base_document_id": "test-bucket/test-document",
        "document_name": "test-document.pdf",
        "total_chunks": 5,
        "completion_time": "2023-01-01T00:10:00",
    }

    # Complete document indexing
    result = complete_document_indexing(message_data)

    # Assertions
    assert result is True
    table_mock.update_item.assert_called_once()


def test_complete_document_indexing_no_document_id():
    """Test completion with no document_id"""
    # Reset mocks
    table_mock.reset_mock()

    # Test data with missing document_id
    message_data = {
        "base_document_id": "test-bucket/test-document",
        "document_name": "test-document.pdf",
        "total_chunks": 5,
    }

    # Should return False when document_id is missing
    result = complete_document_indexing(message_data)

    # Assertions
    assert result is False
    table_mock.update_item.assert_not_called()


def test_complete_document_indexing_error():
    """Test error handling in complete_document_indexing"""
    # Reset mocks
    table_mock.reset_mock()

    # Configure mock to raise exception
    table_mock.update_item.side_effect = Exception("Test exception")

    # Test data
    message_data = {
        "document_id": "test-bucket/test-document/v123456789",
        "total_chunks": 5,
    }

    # Should return False on exception
    result = complete_document_indexing(message_data)

    # Assertions
    assert result is False

    # Reset side_effect for other tests
    table_mock.update_item.side_effect = None


def test_get_document_history():
    """Test getting document history"""
    # Reset mocks
    table_mock.reset_mock()

    # Mock query response
    table_mock.query.return_value = {
        "Items": [
            {"document_id": "test-bucket/test-document/v123456789", "status": "COMPLETED"},
            {"document_id": "test-bucket/test-document/v123456780", "status": "CANCELLED"},
        ]
    }

    # Get history
    result = get_document_history("test-bucket/test-document")

    # Assertions
    assert len(result) == 2
    assert result[0]["status"] == "COMPLETED"
    assert result[1]["status"] == "CANCELLED"
    table_mock.query.assert_called_once()


def test_get_document_history_error():
    """Test error handling in get_document_history"""
    # Reset mocks
    table_mock.reset_mock()

    # Configure mock to raise exception
    table_mock.query.side_effect = Exception("Test exception")

    # Should return empty list on exception
    result = get_document_history("test-bucket/test-document")

    # Assertions
    assert result == []

    # Reset side_effect for other tests
    table_mock.query.side_effect = None


def test_handler_initialize_document_tracking(document_processing_started_event):
    """Test that lambda_handler correctly processes 'Document Processing Started' events"""
    # Use patch to avoid calling the actual implementation
    with patch(
        "src.lambda_functions.document_tracking.handler.initialize_document_tracking",
        return_value=True,
    ) as mock_initialize:
        # Call lambda handler
        response = lambda_handler(document_processing_started_event, {})

        # Assertions
        assert response["statusCode"] == 200
        assert "Processed 1/1 document tracking events" in response["body"]["message"]
        mock_initialize.assert_called_once()


def test_handler_update_indexing_progress(document_chunk_indexed_event):
    """Test that lambda_handler correctly processes 'Document Chunk Indexed' events"""
    # Use patch to avoid calling the actual implementation
    with patch(
        "src.lambda_functions.document_tracking.handler.update_indexing_progress", return_value=True
    ) as mock_update:
        # Call lambda handler
        response = lambda_handler(document_chunk_indexed_event, {})

        # Assertions
        assert response["statusCode"] == 200
        assert "Processed 1/1 document tracking events" in response["body"]["message"]
        mock_update.assert_called_once()


def test_handler_complete_document_indexing(document_indexing_completed_event):
    """Test that lambda_handler correctly processes 'Document Indexing Completed' events"""
    # Use patch to avoid calling the actual implementation
    with patch(
        "src.lambda_functions.document_tracking.handler.complete_document_indexing",
        return_value=True,
    ) as mock_complete:
        # Call lambda handler
        response = lambda_handler(document_indexing_completed_event, {})

        # Assertions
        assert response["statusCode"] == 200
        assert "Processed 1/1 document tracking events" in response["body"]["message"]
        mock_complete.assert_called_once()


def test_handler_with_empty_event():
    """Test that handler handles empty events gracefully"""
    # Setup empty event
    empty_event = {"Records": []}

    # Call lambda handler
    response = lambda_handler(empty_event, {})

    # Assertions
    assert response["statusCode"] == 200
    assert "Processed 0/0 document tracking events" in response["body"]["message"]


def test_handler_with_invalid_message():
    """Test that handler handles invalid messages gracefully"""
    # Setup invalid event
    invalid_event = {
        "Records": [
            {
                "Sns": {"Subject": "Unknown Subject", "Message": "Not valid JSON"},
            }
        ]
    }

    # Call lambda handler
    response = lambda_handler(invalid_event, {})

    # Assertions
    assert response["statusCode"] == 200
    assert "Processed 0/1 document tracking events" in response["body"]["message"]


def test_handler_with_unknown_subject():
    """Test that handler handles unknown message subjects"""
    # Setup event with unknown subject
    unknown_subject_event = {
        "Records": [
            {
                "Sns": {
                    "Subject": "Unknown Subject",
                    "Message": json.dumps({"document_id": "test-id"}),
                },
            }
        ]
    }

    # Call lambda handler
    response = lambda_handler(unknown_subject_event, {})

    # Assertions
    assert response["statusCode"] == 200
    assert "Processed 0/1 document tracking events" in response["body"]["message"]


def test_handler_exception():
    """Test lambda_handler exception handling"""
    # Setup event that will cause an exception
    event = None  # This will cause an exception when accessing event.get()

    # Call lambda handler
    response = lambda_handler(event, {})

    # Assertions
    assert response["statusCode"] == 500
    assert "Error processing SNS events" in response["body"]["message"]
