import json
import unittest
from unittest import mock
import sys

# Create a mock tracking_utils module
tracking_utils_mock = mock.MagicMock()

# Create mock documents list
mock_documents = [
    {
        "document_id": "test-bucket/test.txt/v12345678",
        "base_document_id": "test-bucket/test.txt",
        "document_name": "test.txt",
        "document_version": "v12345678",
        "upload_timestamp": 12345678,
        "status": "COMPLETED",
        "progress": "5/5",
        "start_time": "2023-01-01T00:00:00",
        "completion_time": "2023-01-01T00:05:00",
    },
    {
        "document_id": "test-bucket/sample.pdf/v87654321",
        "base_document_id": "test-bucket/sample.pdf",
        "document_name": "sample.pdf",
        "document_version": "v87654321",
        "upload_timestamp": 87654321,
        "status": "PROCESSING",
        "progress": "3/10",
        "start_time": "2023-01-02T00:00:00",
        "completion_time": "N/A",
    },
]

# Configure the mock to return the documents list
tracking_utils_mock.get_all_documents.return_value = mock_documents

# Apply the mock
sys.modules["src.utils.tracking_utils"] = tracking_utils_mock
sys.modules["utils.tracking_utils"] = tracking_utils_mock

# Now import the handler module
from src.lambda_functions.document_status.handler import lambda_handler


class TestDocumentStatusHandler(unittest.TestCase):
    """
    Test cases for the document_status Lambda function.
    """

    def test_lambda_handler_list_documents(self):
        """
        Test the lambda_handler function to list all documents.
        """
        # Reset mocks before test
        tracking_utils_mock.get_all_documents.reset_mock()

        # Create mock event for GET request
        event = {
            "httpMethod": "GET",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("documents", body)
        self.assertEqual(len(body["documents"]), 2)
        self.assertEqual(body["documents"][0]["document_name"], "test.txt")
        self.assertEqual(body["documents"][1]["document_name"], "sample.pdf")

        # Verify tracking_utils was called correctly
        tracking_utils_mock.get_all_documents.assert_called_once()

    def test_lambda_handler_with_options_method(self):
        """
        Test the lambda_handler function with OPTIONS method (CORS preflight).
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Create mock event with OPTIONS method
        event = {
            "httpMethod": "OPTIONS",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("Access-Control-Allow-Origin", response["headers"])
        body = json.loads(response["body"])
        self.assertIn("CORS preflight", body["message"])

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
            "httpMethod": "GET",
        }

        # Call the function
        response = temp_module.lambda_handler(event, {})

        # Verify the response indicates tracking is not available
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("Document tracking is not available", body["error"])

    def test_lambda_handler_with_exception(self):
        """
        Test the lambda_handler function when an exception occurs.
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Mock get_all_documents to raise an exception
        tracking_utils_mock.get_all_documents.side_effect = Exception("Test error")

        # Create mock event
        event = {
            "httpMethod": "GET",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 500)
        body = json.loads(response["body"])
        self.assertIn("An error occurred while checking document status", body["error"])
        self.assertIn("Test error", body["error"])

        # Reset the mock for other tests
        tracking_utils_mock.get_all_documents.side_effect = None
        tracking_utils_mock.get_all_documents.return_value = mock_documents

    def test_lambda_handler_with_different_http_method(self):
        """
        Test the lambda_handler function with a different HTTP method (not OPTIONS).
        Document status handler treats all methods except OPTIONS the same.
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Create mock event with POST method
        event = {
            "httpMethod": "POST",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response is successful (handler doesn't check for method type except OPTIONS)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("documents", body)

    def test_lambda_handler_with_event_missing_httpmethod(self):
        """
        Test lambda_handler with an event structure missing httpMethod.
        The handler will process this as a regular request since it only checks for OPTIONS.
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Create an event without the httpMethod field
        event = {
            "resource": "/status",
            "path": "/status",
            "headers": {"Content-Type": "application/json"},
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response (handler doesn't validate httpMethod presence)
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("documents", body)

    def test_lambda_handler_with_request_context_format(self):
        """
        Test lambda_handler with API Gateway v2 format.
        """
        # Reset mocks before test
        tracking_utils_mock.get_all_documents.reset_mock()

        # Create event with API Gateway v2 format
        event = {"requestContext": {"http": {"method": "GET"}}}

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("documents", body)
        self.assertEqual(len(body["documents"]), 2)

        # Verify tracking_utils was called correctly
        tracking_utils_mock.get_all_documents.assert_called_once()

    def test_lambda_handler_with_empty_documents_list(self):
        """
        Test lambda_handler when the documents list is empty.
        """
        # Reset mocks before test
        tracking_utils_mock.get_all_documents.reset_mock()

        # Set get_all_documents to return an empty list
        tracking_utils_mock.get_all_documents.return_value = []

        # Create event
        event = {"httpMethod": "GET"}

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        body = json.loads(response["body"])
        self.assertIn("documents", body)
        self.assertEqual(len(body["documents"]), 0)

        # Reset the mock for other tests
        tracking_utils_mock.get_all_documents.return_value = mock_documents


if __name__ == "__main__":
    unittest.main()
