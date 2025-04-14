import json
import unittest
from unittest import mock
import sys
import importlib

# Create a mock tracking_utils module
tracking_utils_mock = mock.MagicMock()
mock_status = {
    "document_name": "test.txt",
    "latest_version": "v12345678",
    "latest_timestamp": 12345678,
    "latest_status": "COMPLETED",
    "versions": 1,
    "versions_processing": 0,
    "history": [
        {
            "version": "v12345678",
            "timestamp": 12345678,
            "status": "COMPLETED",
            "progress": "5/5",
            "start_time": "2023-01-01T00:00:00",
            "completion_time": "2023-01-01T00:05:00",
        }
    ],
}
tracking_utils_mock.get_processing_status.return_value = mock_status

mock_records = [
    {
        "document_id": "test-bucket/test.txt/v12345678",
        "document_name": "test.txt",
        "document_version": "v12345678",
        "status": "COMPLETED",
        "indexed_chunks": 5,
        "total_chunks": 5,
        "start_time": "2023-01-01T00:00:00",
        "completion_time": "2023-01-01T00:05:00",
    }
]
tracking_utils_mock.get_document_history.return_value = mock_records

# Apply the mock
sys.modules["src.utils.tracking_utils"] = tracking_utils_mock
sys.modules["utils.tracking_utils"] = tracking_utils_mock

# Now import the handler module
from src.lambda_functions.document_status.handler import lambda_handler


class TestDocumentStatusHandler(unittest.TestCase):
    """
    Test cases for the document_status Lambda function.
    """

    def test_lambda_handler_with_path_parameter(self):
        """
        Test the lambda_handler function with a path parameter.
        """
        # Reset mocks before test
        tracking_utils_mock.get_processing_status.reset_mock()

        # Create mock event with path parameter
        event = {
            "pathParameters": {"document_id": "test-bucket/test.txt"},
            "httpMethod": "GET",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["latest_status"], "COMPLETED")
        self.assertEqual(body["document_name"], "test.txt")

        # Verify tracking_utils was called correctly
        tracking_utils_mock.get_processing_status.assert_called_with("test-bucket/test.txt")

    def test_lambda_handler_with_query_parameter(self):
        """
        Test the lambda_handler function with query parameters.
        """
        # Reset mocks before test
        tracking_utils_mock.get_document_history.reset_mock()

        # Create a specific mock for this test case
        specific_mock_record = {
            "document_id": "test-bucket/test.txt/v12345678",
            "document_name": "test.txt",
            "document_version": "v12345678",
            "status": "COMPLETED",
            "indexed_chunks": 5,
            "total_chunks": 5,
            "start_time": "2023-01-01T00:00:00",
            "completion_time": "2023-01-01T00:05:00",
        }
        tracking_utils_mock.get_document_history.return_value = [specific_mock_record]

        # Create mock event with query parameters
        event = {
            "queryStringParameters": {
                "document_id": "test-bucket/test.txt/v12345678",  # Use full document ID
                "use_base_id": "false",
            },
            "httpMethod": "GET",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "COMPLETED")

        # Verify tracking_utils was called with the base document ID
        tracking_utils_mock.get_document_history.assert_called_with("test-bucket/test.txt")

    def test_lambda_handler_with_post_body(self):
        """
        Test the lambda_handler function with a POST body.
        """
        # Reset mocks before test
        tracking_utils_mock.get_processing_status.reset_mock()

        # Create mock event with POST body
        event = {
            "body": json.dumps({"document_id": "test-bucket/test.txt", "use_base_id": True}),
            "httpMethod": "POST",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["latest_status"], "COMPLETED")

        # Verify tracking_utils was called correctly
        tracking_utils_mock.get_processing_status.assert_called_with("test-bucket/test.txt")

    def test_lambda_handler_with_options_method(self):
        """
        Test the lambda_handler function with OPTIONS method (CORS preflight).
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Create mock event with OPTIONS method
        event = {
            "pathParameters": {"document_id": "test-bucket/test.txt"},
            "httpMethod": "OPTIONS",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", response["headers"])
        body = json.loads(response["body"])
        self.assertIn("CORS preflight", body["message"])

    def test_lambda_handler_with_missing_document_id(self):
        """
        Test the lambda_handler function with missing document_id.
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Create mock event with no document_id
        event = {
            "queryStringParameters": {},
            "httpMethod": "GET",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("Missing document_id", body["error"])

    def test_lambda_handler_with_invalid_json(self):
        """
        Test the lambda_handler function with invalid JSON body.
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Create mock event with invalid JSON
        event = {
            "body": "{invalid-json",
            "httpMethod": "POST",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("Invalid JSON", body["error"])

    def test_lambda_handler_with_exception(self):
        """
        Test the lambda_handler function when an exception occurs.
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Mock tracking_utils.get_processing_status to raise an exception
        tracking_utils_mock.get_processing_status.side_effect = Exception("Test error")

        # Create mock event
        event = {
            "pathParameters": {"document_id": "test-bucket/test.txt"},
            "httpMethod": "GET",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("An error occurred", body["error"])
        self.assertIn("Test error", body["error"])

        # Reset the mock for other tests
        tracking_utils_mock.get_processing_status.side_effect = None
        tracking_utils_mock.get_processing_status.return_value = mock_status

    def test_when_tracking_utils_is_none(self):
        """
        Test the lambda_handler function when tracking_utils is None.
        """

        # Create a temporary module with tracking_utils = None
        class TempModule:
            lambda_handler = None

        temp_module = TempModule()

        # Get the original module
        import src.lambda_functions.document_status.handler as original_module

        # Create a modified version of the handler with tracking_utils = None
        original_code = original_module.lambda_handler.__code__

        # Create a copy of the original handler function to modify
        def temp_handler(event, context):
            # Mock that tracking_utils is None
            original_tracking = original_module.tracking_utils
            original_module.tracking_utils = None

            try:
                result = original_module.lambda_handler(event, context)
            finally:
                # Restore tracking_utils
                original_module.tracking_utils = original_tracking

            return result

        temp_module.lambda_handler = temp_handler

        # Create mock event
        event = {
            "pathParameters": {"document_id": "test-bucket/test.txt"},
            "httpMethod": "GET",
        }

        # Call the function
        response = temp_module.lambda_handler(event, {})

        # Verify the response indicates tracking is not available
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("Document tracking is not available", body["error"])

    def test_document_not_found(self):
        """
        Test the lambda_handler function when document is not found in records.
        """
        # Reset mocks before test
        tracking_utils_mock.get_document_history.reset_mock()

        # Set up the mock to return empty records
        tracking_utils_mock.get_document_history.return_value = []

        # Create mock event with query parameters for non-existent document
        event = {
            "queryStringParameters": {
                "document_id": "non-existent-doc/unknown.txt/v99999999",
                "use_base_id": "false",
            },
            "httpMethod": "GET",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertEqual(body["status"], "NOT_FOUND")
        self.assertIn("No record found", body["message"])

        # Reset the mock for other tests
        tracking_utils_mock.get_document_history.return_value = mock_records

    def test_base_id_parts_parsing(self):
        """
        Test the base_id_parts parsing logic with different formats.
        """
        # Test with standard 3-part ID
        # Reset mocks before test
        tracking_utils_mock.get_document_history.reset_mock()

        event = {
            "queryStringParameters": {
                "document_id": "test-bucket/test.txt/v12345678",
                "use_base_id": "false",
            },
            "httpMethod": "GET",
        }

        lambda_handler(event, {})
        tracking_utils_mock.get_document_history.assert_called_with("test-bucket/test.txt")

        # Test with single-part ID (edge case)
        tracking_utils_mock.get_document_history.reset_mock()

        event = {
            "queryStringParameters": {
                "document_id": "singledocument",
                "use_base_id": "false",
            },
            "httpMethod": "GET",
        }

        lambda_handler(event, {})
        tracking_utils_mock.get_document_history.assert_called_with("singledocument")


if __name__ == "__main__":
    unittest.main()
