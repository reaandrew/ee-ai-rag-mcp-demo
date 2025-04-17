import json
import unittest
from unittest import mock
import sys
import decimal

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
from src.lambda_functions.document_status.handler import lambda_handler, DecimalEncoder


class TestDecimalEncoder(unittest.TestCase):
    """Test cases for the DecimalEncoder class."""

    def test_decimal_encoder_integer(self):
        """Test that DecimalEncoder correctly converts integer Decimal objects."""
        test_decimal = decimal.Decimal("10")
        result = json.dumps(test_decimal, cls=DecimalEncoder)
        self.assertEqual(result, "10")

    def test_decimal_encoder_float(self):
        """Test that DecimalEncoder correctly converts float Decimal objects."""
        test_decimal = decimal.Decimal("10.5")
        result = json.dumps(test_decimal, cls=DecimalEncoder)
        self.assertEqual(result, "10.5")

    def test_decimal_encoder_nested(self):
        """Test that DecimalEncoder correctly handles nested structures with Decimals."""
        test_data = {
            "int_value": decimal.Decimal("10"),
            "float_value": decimal.Decimal("10.5"),
            "nested": {"decimal_value": decimal.Decimal("5.25")},
        }
        result = json.dumps(test_data, cls=DecimalEncoder)
        self.assertEqual(
            json.loads(result),
            {"int_value": 10, "float_value": 10.5, "nested": {"decimal_value": 5.25}},
        )

    def test_decimal_encoder_non_decimal(self):
        """Test that DecimalEncoder correctly handles non-Decimal objects."""
        test_data = {"string": "test", "number": 42, "bool": True, "list": [1, 2, 3]}
        result = json.dumps(test_data, cls=DecimalEncoder)
        self.assertEqual(json.loads(result), test_data)


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

    def test_lambda_handler_with_unsupported_method(self):
        """
        Test the lambda_handler function with an unsupported HTTP method.
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Create mock event with unsupported method
        event = {
            "httpMethod": "POST",
        }

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("error", body)
        self.assertIn("Unsupported method", body["error"])

    def test_lambda_handler_missing_method(self):
        """
        Test the lambda_handler function when httpMethod is missing.
        """
        # Reset all mocks before test
        tracking_utils_mock.reset_mock()

        # Create mock event without httpMethod
        event = {}

        # Call the function
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 400)
        body = json.loads(response["body"])
        self.assertIn("error", body)
        self.assertIn("Missing httpMethod in event", body["error"])

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


if __name__ == "__main__":
    unittest.main()
