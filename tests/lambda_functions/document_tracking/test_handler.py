import json
import unittest
from unittest import mock

# Import the handler and functions
from src.lambda_functions.document_tracking.handler import (
    lambda_handler,
    initialize_document_tracking,
    update_indexing_progress,
    complete_document_indexing,
    DecimalEncoder,
)


class TestDecimalEncoder(unittest.TestCase):
    """Test cases for the DecimalEncoder class."""

    def test_decimal_encoder(self):
        """Test that DecimalEncoder correctly converts Decimal objects."""
        from decimal import Decimal

        # Test integer decimals
        self.assertEqual(json.dumps(Decimal("10"), cls=DecimalEncoder), "10")

        # Test float decimals
        self.assertEqual(json.dumps(Decimal("10.5"), cls=DecimalEncoder), "10.5")

        # Test nested structures with decimals
        data = {"int": Decimal("10"), "float": Decimal("10.5")}
        self.assertEqual(json.dumps(data, cls=DecimalEncoder), '{"int": 10, "float": 10.5}')


class TestDocumentTrackingHandler(unittest.TestCase):
    """Test cases for the document_tracking Lambda handler."""

    def setUp(self):
        """Set up test fixtures."""
        # Create a patcher for boto3 resource
        self.boto3_resource_patcher = mock.patch("boto3.resource")
        self.mock_boto3_resource = self.boto3_resource_patcher.start()

        # Mock the DynamoDB resource and table
        self.mock_table = mock.MagicMock()
        self.mock_dynamodb = mock.MagicMock()
        self.mock_boto3_resource.return_value = self.mock_dynamodb
        self.mock_dynamodb.Table.return_value = self.mock_table

        # Set up default return values
        self.mock_table.put_item.return_value = {}
        self.mock_table.update_item.return_value = {"Attributes": {"indexed_chunks": 1}}
        self.mock_table.get_item.return_value = {"Item": {"total_chunks": 5, "indexed_chunks": 0}}
        self.mock_table.query.return_value = {"Items": []}

    def tearDown(self):
        """Tear down test fixtures."""
        self.boto3_resource_patcher.stop()

    def test_lambda_handler_with_empty_event(self):
        """Test handler with an empty event."""
        event = {"Records": []}
        response = lambda_handler(event, {})

        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["message"], "Processed 0 SNS events")
        self.assertEqual(len(response["body"]["results"]), 0)

    def test_lambda_handler_with_init_message(self):
        """Test handler with a Document Processing Started message."""
        # Create a test SNS event
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "base_document_id": "test-bucket/test-doc",
            "document_name": "test-doc.pdf",
            "document_version": "v1234567890",
            "upload_timestamp": 1234567890,
            "total_chunks": 5,
        }

        event = {
            "Records": [
                {
                    "Sns": {
                        "Subject": "Document Processing Started",
                        "Message": json.dumps(message_data),
                    }
                }
            ]
        }

        # Call the handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["message"], "Processed 1 SNS events")
        self.assertEqual(len(response["body"]["results"]), 1)
        self.assertEqual(response["body"]["results"][0]["status"], "success")
        self.assertEqual(response["body"]["results"][0]["document_id"], message_data["document_id"])

    def test_lambda_handler_with_progress_message(self):
        """Test handler with a Document Chunk Indexed message."""
        # Create a test SNS event
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "document_name": "test-doc.pdf",
            "page_number": 2,
            "progress": "3/5",
        }

        event = {
            "Records": [
                {"Sns": {"Subject": "Document Chunk Indexed", "Message": json.dumps(message_data)}}
            ]
        }

        # Call the handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["message"], "Processed 1 SNS events")
        self.assertEqual(len(response["body"]["results"]), 1)
        self.assertEqual(response["body"]["results"][0]["status"], "success")
        self.assertEqual(response["body"]["results"][0]["document_id"], message_data["document_id"])
        # Progress is now calculated internally, not taken from message
        self.assertIn("progress", response["body"]["results"][0])  # Just verify it exists

    def test_lambda_handler_with_completion_message(self):
        """Test handler with a Document Indexing Completed message."""
        # Create a test SNS event
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "document_name": "test-doc.pdf",
            "total_chunks": 5,
            "completion_time": "2023-01-01T12:30:00",
        }

        event = {
            "Records": [
                {
                    "Sns": {
                        "Subject": "Document Indexing Completed",
                        "Message": json.dumps(message_data),
                    }
                }
            ]
        }

        # Call the handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["message"], "Processed 1 SNS events")
        self.assertEqual(len(response["body"]["results"]), 1)
        self.assertEqual(response["body"]["results"][0]["status"], "success")
        self.assertEqual(response["body"]["results"][0]["document_id"], message_data["document_id"])

    def test_lambda_handler_with_unknown_subject(self):
        """Test handler with an unknown message subject."""
        # Create a test SNS event
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "document_name": "test-doc.pdf",
            "total_chunks": 5,
        }

        event = {
            "Records": [
                {"Sns": {"Subject": "Unknown Subject", "Message": json.dumps(message_data)}}
            ]
        }

        # Call the handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["message"], "Processed 1 SNS events")
        self.assertEqual(len(response["body"]["results"]), 1)
        self.assertEqual(response["body"]["results"][0]["status"], "success")
        self.assertIn("Unknown Subject", response["body"]["results"][0]["message"])

    def test_lambda_handler_with_invalid_message(self):
        """Test handler with an invalid JSON message."""
        event = {
            "Records": [
                {
                    "Sns": {
                        "Subject": "Document Processing Started",
                        "Message": "this is not valid json",
                    }
                }
            ]
        }

        # Call the handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(response["body"]["message"], "Processed 1 SNS events")
        self.assertEqual(len(response["body"]["results"]), 1)
        self.assertEqual(response["body"]["results"][0]["status"], "error")

    def test_lambda_handler_exception(self):
        """Test handler when an exception occurs."""
        event = {"malformed": "event"}  # Will cause an exception

        # Mock the logger to prevent error messages in test output
        with mock.patch("src.lambda_functions.document_tracking.handler.logger.error"):
            # Call the handler
            response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 500)
        self.assertIn("Error processing SNS events", response["body"]["message"])

    def test_initialize_document_tracking_new_document(self):
        """Test initialize_document_tracking with complete data."""
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "base_document_id": "test-bucket/test-doc",
            "document_name": "test-doc.pdf",
            "document_version": "v1234567890",
            "upload_timestamp": 1234567890,
            "total_chunks": 5,
            "status": "PROCESSING",
            "start_time": "2023-01-01T12:00:00",
        }

        # Call the function
        result = initialize_document_tracking(message_data)

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["document_id"], message_data["document_id"])

    def test_initialize_document_tracking_error(self):
        """Test initialize_document_tracking with missing required fields."""
        # Missing required fields
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890"
            # Missing base_document_id, document_name, total_chunks
        }

        # Call the function
        result = initialize_document_tracking(message_data)

        # Verify the result
        self.assertEqual(result["status"], "error")
        self.assertIn("Missing required fields", result["message"])

    def test_update_indexing_progress_with_progress(self):
        """Test update_indexing_progress with complete data."""
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "document_name": "test-doc.pdf",
            "page_number": 1,
            "progress": "3/5",
        }

        # Call the function
        result = update_indexing_progress(message_data)

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["document_id"], message_data["document_id"])
        # Progress is now calculated internally, not taken from message
        self.assertIn("progress", result)  # Just verify it exists

    def test_update_indexing_progress_error(self):
        """Test update_indexing_progress with missing required fields."""
        # Missing required fields
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890"
            # Missing document_name, page_number
        }

        # Call the function
        result = update_indexing_progress(message_data)

        # Verify the result
        self.assertEqual(result["status"], "error")
        self.assertIn("Missing required fields", result["message"])

    def test_complete_document_indexing_success(self):
        """Test complete_document_indexing with complete data."""
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "document_name": "test-doc.pdf",
            "total_chunks": 5,
            "completion_time": "2023-01-01T12:30:00",
        }

        # Call the function
        result = complete_document_indexing(message_data)

        # Verify the result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["document_id"], message_data["document_id"])

    def test_complete_document_indexing_error(self):
        """Test complete_document_indexing with missing required fields."""
        # Missing required fields
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890"
            # Missing document_name, total_chunks
        }

        # Call the function
        result = complete_document_indexing(message_data)

        # Verify the result
        self.assertEqual(result["status"], "error")
        self.assertIn("Missing required fields", result["message"])

    def test_complete_document_indexing_conditional_check_failure(self):
        """Test complete_document_indexing with ConditionalCheckFailedException."""
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "document_name": "test-doc.pdf",
            "total_chunks": 5,
            "completion_time": "2023-01-01T12:30:00",
        }

        # Configure mock to throw a ConditionalCheckFailedException
        from botocore.exceptions import ClientError

        error_response = {"Error": {"Code": "ConditionalCheckFailedException"}}
        conditional_error = ClientError(error_response, "update_item")
        self.mock_table.update_item.side_effect = conditional_error

        # Mock the get_item response for the already completed document
        self.mock_table.get_item.return_value = {
            "Item": {
                "document_id": "test-bucket/test-doc/v1234567890",
                "status": "COMPLETED",
                "total_chunks": 5,
                "indexed_chunks": 5,
            }
        }

        # Call the function
        result = complete_document_indexing(message_data)

        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["document_id"], message_data["document_id"])

        # Verify get_item was called
        self.mock_table.get_item.assert_called_with(
            Key={"document_id": message_data["document_id"]}
        )

    def test_get_document_history(self):
        """Test get_document_history function."""
        from src.lambda_functions.document_tracking.handler import get_document_history

        base_document_id = "test-bucket/test-doc"
        mock_history_items = [
            {
                "document_id": "test-bucket/test-doc/v1234567891",
                "status": "COMPLETED",
                "upload_timestamp": 1234567891,
            },
            {
                "document_id": "test-bucket/test-doc/v1234567890",
                "status": "COMPLETED",
                "upload_timestamp": 1234567890,
            },
        ]

        # Configure the mock to return history items
        self.mock_table.query.return_value = {"Items": mock_history_items}

        # Call the function
        result = get_document_history(base_document_id)

        # Verify result
        self.assertEqual(result, mock_history_items)

        # Verify query parameters
        self.mock_table.query.assert_called_with(
            IndexName="BaseDocumentIndex", KeyConditionExpression=mock.ANY, ScanIndexForward=False
        )

    def test_get_document_history_error(self):
        """Test get_document_history when an error occurs."""
        from src.lambda_functions.document_tracking.handler import get_document_history

        base_document_id = "test-bucket/test-doc"

        # Configure the mock to throw an exception
        self.mock_table.query.side_effect = Exception("Test error")

        # Call the function
        result = get_document_history(base_document_id)

        # Verify that an empty list is returned on error
        self.assertEqual(result, [])

    def test_update_indexing_progress_complete(self):
        """Test update_indexing_progress when all chunks are processed."""
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "document_name": "test-doc.pdf",
            "page_number": 5,
            "progress": "5/5",
        }

        # Configure the mock for a document that will be completed
        self.mock_table.get_item.return_value = {
            "Item": {
                "document_id": "test-bucket/test-doc/v1234567890",
                "total_chunks": 5,
                "indexed_chunks": 4,
                "status": "PROCESSING",
            }
        }

        # Configure update_item to return new indexed_chunks value = total_chunks
        self.mock_table.update_item.return_value = {"Attributes": {"indexed_chunks": 5}}

        # Call the function
        result = update_indexing_progress(message_data)

        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["document_id"], message_data["document_id"])
        self.assertEqual(result["progress"], "5/5")

        # Verify the table was updated to mark as COMPLETED
        # The third update_item call will be for setting COMPLETED status
        self.assertEqual(self.mock_table.update_item.call_count, 3)

    def test_update_indexing_progress_for_problematic_document(self):
        """Test update_indexing_progress with a problematic document."""
        message_data = {
            "document_id": "test-bucket/test-doc/v1234567890",
            "document_name": "internet_usage_policy.txt",  # This is one of the problematic docs
            "page_number": 2,
            "progress": "2/5",
        }

        # Configure the mock for document status
        self.mock_table.get_item.return_value = {
            "Item": {
                "document_id": "test-bucket/test-doc/v1234567890",
                "total_chunks": 5,
                "indexed_chunks": 1,
                "status": "PROCESSING",
            }
        }

        # Call the function
        result = update_indexing_progress(message_data)

        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["document_id"], message_data["document_id"])
        self.assertEqual(result["document_name"], "internet_usage_policy.txt")

        # Since it's a problematic document, there should be extra logs but same functionality


if __name__ == "__main__":
    unittest.main()
