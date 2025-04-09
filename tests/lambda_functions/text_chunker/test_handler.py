import json
import unittest
from unittest import mock
from datetime import datetime
import boto3
from botocore.stub import Stubber
import os
import sys

# Mock the langchain modules
sys.modules["langchain"] = mock.MagicMock()
sys.modules["langchain_text_splitters"] = mock.MagicMock()
RecursiveCharacterTextSplitterMock = mock.MagicMock()
RecursiveCharacterTextSplitterMock.return_value.split_text.return_value = [
    "This is chunk 1.",
]
sys.modules[
    "langchain_text_splitters"
].RecursiveCharacterTextSplitter = RecursiveCharacterTextSplitterMock

# Import the Lambda handler
from src.lambda_functions.text_chunker.handler import (
    lambda_handler,
    process_text_file,
    chunk_text,
    CHUNKED_TEXT_BUCKET,
    CHUNKED_TEXT_PREFIX,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
)


class TestTextChunkerHandler(unittest.TestCase):
    """
    Test cases for the text_chunker Lambda function.
    """

    def setUp(self):
        """
        Set up test fixtures before each test.
        """
        # Create a mock S3 client
        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.s3_stubber = Stubber(self.s3_client)

        # Create patchers for the boto3 clients within the handler module
        self.s3_client_patch = mock.patch(
            "src.lambda_functions.text_chunker.handler.s3_client", self.s3_client
        )

        self.s3_client_patch.start()

    def tearDown(self):
        """
        Clean up resources after each test.
        """
        # Stop the patchers
        self.s3_client_patch.stop()

    def test_chunk_text(self):
        """
        Test the chunk_text function.
        """
        # Define test data
        test_text = """This is a test document. It has multiple sentences and should be split into chunks.
        
        This is a second paragraph. It provides more text to ensure we have enough content for chunking.
        
        This is the third paragraph with even more text to make sure we get several chunks from the text splitter."""

        metadata = {
            "source_bucket": "test-bucket",
            "source_key": "test.txt",
            "filename": "test.txt",
        }

        # Call the function
        chunks = chunk_text(test_text, metadata)

        # Verify the result
        self.assertIsInstance(chunks, list)
        self.assertGreater(len(chunks), 0)

        # Check each chunk has the expected properties
        for i, chunk in enumerate(chunks):
            self.assertEqual(chunk["chunk_id"], i)
            self.assertEqual(chunk["total_chunks"], len(chunks))
            self.assertIn("text", chunk)
            self.assertIn("chunk_size", chunk)
            self.assertEqual(chunk["chunk_size"], len(chunk["text"]))
            self.assertIn("metadata", chunk)
            self.assertEqual(chunk["metadata"]["source_bucket"], "test-bucket")

    def test_process_text_file(self):
        """
        Test the process_text_file function.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "sample.txt"
        content_length = 1234
        last_modified = datetime.now()
        text_content = "This is a sample text document for testing the chunking process."

        # Stub the head_object method to return our test data
        self.s3_stubber.add_response(
            "head_object",
            {
                "ContentLength": content_length,
                "LastModified": last_modified,
                "ContentType": "text/plain",
            },
            {"Bucket": bucket_name, "Key": file_key},
        )

        # Stub the get_object method
        self.s3_stubber.add_response(
            "get_object",
            {
                "Body": mock.MagicMock(read=lambda: text_content.encode("utf-8")),
                "ContentType": "text/plain",
                "ContentLength": len(text_content),
            },
            {"Bucket": bucket_name, "Key": file_key},
        )

        # Stub the put_object method for saving all three chunks
        filename_without_ext = "sample"

        # Add response for the one chunk that our mock will create
        chunk_key = f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/chunk_0.json"
        self.s3_stubber.add_response(
            "put_object",
            {},
            {
                "Bucket": CHUNKED_TEXT_BUCKET,
                "Key": chunk_key,
                "Body": mock.ANY,
                "ContentType": "application/json",
            },
        )

        # Stub the put_object method for saving the manifest
        manifest_key = f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/manifest.json"
        self.s3_stubber.add_response(
            "put_object",
            {},
            {
                "Bucket": CHUNKED_TEXT_BUCKET,
                "Key": manifest_key,
                "Body": mock.ANY,
                "ContentType": "application/json",
            },
        )

        # Activate the stubber
        self.s3_stubber.activate()

        # Call the function
        result = process_text_file(bucket_name, file_key)

        # Verify the result
        self.assertEqual(result["source"]["bucket"], bucket_name)
        self.assertEqual(result["source"]["file_key"], file_key)
        self.assertEqual(result["status"], "success")

        # Verify output information
        self.assertIn("output", result)
        self.assertEqual(result["output"]["bucket"], CHUNKED_TEXT_BUCKET)
        self.assertEqual(result["output"]["manifest_key"], manifest_key)
        self.assertEqual(
            result["output"]["total_chunks"], 1
        )  # We expect exactly 1 chunk from our mock

        # Verify that the stubber was used correctly
        self.s3_stubber.assert_no_pending_responses()

    def test_lambda_handler_with_valid_event(self):
        """
        Test the lambda_handler function with a valid S3 event.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "sample.txt"
        content_length = 1234
        last_modified = datetime.now()
        text_content = "This is a sample text document for testing the chunking process."

        # Create a mock S3 event
        event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "s3": {"bucket": {"name": bucket_name}, "object": {"key": file_key}},
                }
            ]
        }

        # Stub the head_object method to return our test data
        self.s3_stubber.add_response(
            "head_object",
            {
                "ContentLength": content_length,
                "LastModified": last_modified,
                "ContentType": "text/plain",
            },
            {"Bucket": bucket_name, "Key": file_key},
        )

        # Stub the get_object method
        self.s3_stubber.add_response(
            "get_object",
            {
                "Body": mock.MagicMock(read=lambda: text_content.encode("utf-8")),
                "ContentType": "text/plain",
                "ContentLength": len(text_content),
            },
            {"Bucket": bucket_name, "Key": file_key},
        )

        # Stub the put_object method for saving all three chunks
        filename_without_ext = "sample"

        # Add response for the one chunk that our mock will create
        chunk_key = f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/chunk_0.json"
        self.s3_stubber.add_response(
            "put_object",
            {},
            {
                "Bucket": CHUNKED_TEXT_BUCKET,
                "Key": chunk_key,
                "Body": mock.ANY,
                "ContentType": "application/json",
            },
        )

        # Stub the put_object method for saving the manifest
        manifest_key = f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/manifest.json"
        self.s3_stubber.add_response(
            "put_object",
            {},
            {
                "Bucket": CHUNKED_TEXT_BUCKET,
                "Key": manifest_key,
                "Body": mock.ANY,
                "ContentType": "application/json",
            },
        )

        # Activate the stubber
        self.s3_stubber.activate()

        # Call the lambda handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("message", response["body"])
        self.assertIn("results", response["body"])
        self.assertEqual(len(response["body"]["results"]), 1)

        # Verify the saved output details
        result = response["body"]["results"][0]
        self.assertIn("output", result)
        self.assertEqual(result["output"]["bucket"], CHUNKED_TEXT_BUCKET)

        # Verify that the stubber was used correctly
        self.s3_stubber.assert_no_pending_responses()

    def test_lambda_handler_with_non_text_file(self):
        """
        Test the lambda_handler function with a non-text file.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "sample.pdf"

        # Create a mock S3 event
        event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "s3": {"bucket": {"name": bucket_name}, "object": {"key": file_key}},
                }
            ]
        }

        # Call the lambda handler (should skip non-text files)
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("message", response["body"])
        self.assertIn("results", response["body"])
        self.assertEqual(len(response["body"]["results"]), 0)

    def test_lambda_handler_with_no_records(self):
        """
        Test the lambda_handler function with an event that has no records.
        """
        # Create a mock S3 event with no records
        event = {"Records": []}

        # Call the lambda handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("message", response["body"])
        self.assertIn("results", response["body"])
        self.assertEqual(len(response["body"]["results"]), 0)

    def test_process_text_file_exception(self):
        """
        Test the process_text_file function when an exception occurs.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "sample.txt"

        # Make the S3 client raise an exception when head_object is called
        self.s3_stubber.add_client_error(
            "head_object",
            service_error_code="NoSuchKey",
            service_message="The specified key does not exist.",
            http_status_code=404,
            expected_params={"Bucket": bucket_name, "Key": file_key},
        )

        # Activate the stubber
        self.s3_stubber.activate()

        # Patch the logger to prevent error messages from showing in test output
        with mock.patch("src.lambda_functions.text_chunker.handler.logger.error"):
            # Call the function and expect an exception
            with self.assertRaises(Exception):
                process_text_file(bucket_name, file_key)

        # Verify that the stubber was used correctly
        self.s3_stubber.assert_no_pending_responses()

    def test_lambda_handler_with_exception(self):
        """
        Test the lambda_handler function when an exception occurs.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "sample.txt"

        # Create a mock S3 event
        event = {
            "Records": [
                {
                    "eventSource": "aws:s3",
                    "s3": {"bucket": {"name": bucket_name}, "object": {"key": file_key}},
                }
            ]
        }

        # Make the S3 client raise an exception when head_object is called
        self.s3_stubber.add_client_error(
            "head_object",
            service_error_code="NoSuchKey",
            service_message="The specified key does not exist.",
            http_status_code=404,
            expected_params={"Bucket": bucket_name, "Key": file_key},
        )

        # Activate the stubber
        self.s3_stubber.activate()

        # Patch the loggers to prevent error messages from showing in test output
        with mock.patch("src.lambda_functions.text_chunker.handler.logger.error"):
            # Call the lambda handler
            response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 500)
        self.assertIn("message", response["body"])
        self.assertIn("Error processing text files", response["body"]["message"])

        # Verify that the stubber was used correctly
        self.s3_stubber.assert_no_pending_responses()


if __name__ == "__main__":
    unittest.main()
