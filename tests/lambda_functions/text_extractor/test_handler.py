import json
import unittest
from unittest import mock
from datetime import datetime
import boto3
from botocore.stub import Stubber

# Import the Lambda handler
from src.lambda_functions.text_extractor.handler import lambda_handler, extract_text_from_pdf, process_document_async


class TestTextExtractorHandler(unittest.TestCase):
    """
    Test cases for the text_extractor Lambda function.
    """

    def setUp(self):
        """
        Set up test fixtures before each test.
        """
        # Create a mock S3 client
        self.s3_client = boto3.client("s3", region_name="us-east-1")
        self.s3_stubber = Stubber(self.s3_client)

        # Create a mock Textract client
        self.textract_client = boto3.client("textract", region_name="us-east-1")
        self.textract_stubber = Stubber(self.textract_client)

        # Create patchers for the boto3 clients within the handler module
        self.s3_client_patch = mock.patch(
            "src.lambda_functions.text_extractor.handler.s3_client", self.s3_client
        )
        self.textract_client_patch = mock.patch(
            "src.lambda_functions.text_extractor.handler.textract_client", self.textract_client
        )

        self.s3_client_patch.start()
        self.textract_client_patch.start()

    def tearDown(self):
        """
        Clean up resources after each test.
        """
        # Stop the patchers
        self.s3_client_patch.stop()
        self.textract_client_patch.stop()

    def test_extract_text_from_pdf(self):
        """
        Test the extract_text_from_pdf function.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "sample.pdf"
        content_length = 12345
        last_modified = datetime.now()

        # Stub the head_object method to return our test data
        self.s3_stubber.add_response(
            "head_object",
            {
                "ContentLength": content_length,
                "LastModified": last_modified,
                "ContentType": "application/pdf",
            },
            {"Bucket": bucket_name, "Key": file_key},
        )

        # Stub the Textract response
        self.textract_stubber.add_response(
            "detect_document_text",
            {
                "DocumentMetadata": {"Pages": 1},
                "Blocks": [
                    {
                        "BlockType": "LINE",
                        "Text": "Sample text from PDF.",
                        "Id": "1",
                        "Confidence": 99.0,
                    }
                ],
            },
            {"Document": {"S3Object": {"Bucket": bucket_name, "Name": file_key}}},
        )

        # Activate the stubbers
        self.s3_stubber.activate()
        self.textract_stubber.activate()

        # Call the function
        result = extract_text_from_pdf(bucket_name, file_key)

        # Verify the result
        self.assertEqual(result["source"]["bucket"], bucket_name)
        self.assertEqual(result["source"]["file_key"], file_key)
        self.assertEqual(result["source"]["size_bytes"], content_length)
        self.assertIn("extracted_text", result)
        self.assertIn("Sample text from PDF.", result["extracted_text"])
        self.assertEqual(result["status"], "success")

        # Verify that the stubbers were used correctly
        self.s3_stubber.assert_no_pending_responses()
        self.textract_stubber.assert_no_pending_responses()

    def test_lambda_handler_with_valid_event(self):
        """
        Test the lambda_handler function with a valid S3 event.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "sample.pdf"
        content_length = 12345
        last_modified = datetime.now()

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
                "ContentType": "application/pdf",
            },
            {"Bucket": bucket_name, "Key": file_key},
        )

        # Stub the Textract response
        self.textract_stubber.add_response(
            "detect_document_text",
            {
                "DocumentMetadata": {"Pages": 1},
                "Blocks": [
                    {
                        "BlockType": "LINE",
                        "Text": "Sample text from PDF.",
                        "Id": "1",
                        "Confidence": 99.0,
                    }
                ],
            },
            {"Document": {"S3Object": {"Bucket": bucket_name, "Name": file_key}}},
        )

        # Activate the stubbers
        self.s3_stubber.activate()
        self.textract_stubber.activate()

        # Call the lambda handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 200)
        self.assertIn("message", response["body"])
        self.assertIn("results", response["body"])
        self.assertEqual(len(response["body"]["results"]), 1)

        # Verify that the stubbers were used correctly
        self.s3_stubber.assert_no_pending_responses()
        self.textract_stubber.assert_no_pending_responses()

    def test_lambda_handler_with_non_pdf_file(self):
        """
        Test the lambda_handler function with a non-PDF file.
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

        # Call the lambda handler
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

    def test_extract_text_from_pdf_exception(self):
        """
        Test the extract_text_from_pdf function when an exception occurs.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "sample.pdf"

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

        # Call the function and expect an exception
        with self.assertRaises(Exception):
            extract_text_from_pdf(bucket_name, file_key)

        # Verify that the stubber was used correctly
        self.s3_stubber.assert_no_pending_responses()

    def test_extract_text_from_pdf_large_document_fallback(self):
        """
        Test the extract_text_from_pdf function with a large document that
        requires fallback to async processing.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "large-sample.pdf"
        content_length = 54321
        last_modified = datetime.now()
        job_id = "fallback-job-id"

        # Stub the head_object method to return our test data
        self.s3_stubber.add_response(
            "head_object",
            {
                "ContentLength": content_length,
                "LastModified": last_modified,
                "ContentType": "application/pdf",
            },
            {"Bucket": bucket_name, "Key": file_key},
        )

        # Stub the Textract detect_document_text to raise an InvalidParameterException for page limit
        self.textract_stubber.add_client_error(
            "detect_document_text",
            service_error_code="InvalidParameterException",
            service_message="Page limit exceeded. The document has more pages than allowed.",
            http_status_code=400,
            expected_params={
                "Document": {
                    "S3Object": {
                        "Bucket": bucket_name,
                        "Name": file_key
                    }
                }
            }
        )
        
        # Then mock responses for the async process which should be called for fallback
        # 1. Start async job
        self.textract_stubber.add_response(
            "start_document_text_detection",
            {"JobId": job_id},
            {
                "DocumentLocation": {
                    "S3Object": {"Bucket": bucket_name, "Name": file_key}
                }
            }
        )
        
        # 2. Check job status
        self.textract_stubber.add_response(
            "get_document_text_detection",
            {
                "JobStatus": "SUCCEEDED",
                "DocumentMetadata": {"Pages": 6}
            },
            {"JobId": job_id}
        )
        
        # 3. Get results
        self.textract_stubber.add_response(
            "get_document_text_detection",
            {
                "JobStatus": "SUCCEEDED",
                "DocumentMetadata": {"Pages": 6},
                "Blocks": [
                    {
                        "BlockType": "LINE",
                        "Text": "Large document text from multiple pages.",
                        "Id": "1",
                        "Confidence": 95.0
                    }
                ]
                # No NextToken since we're simplifying the test
            },
            {"JobId": job_id}
        )

        # Activate the stubbers
        self.s3_stubber.activate()
        self.textract_stubber.activate()

        # Call the function
        result = extract_text_from_pdf(bucket_name, file_key)

        # Verify the result
        self.assertEqual(result["source"]["bucket"], bucket_name)
        self.assertEqual(result["source"]["file_key"], file_key)
        self.assertEqual(result["source"]["size_bytes"], content_length)
        self.assertIn("extracted_text", result)
        self.assertIn("Large document text from multiple pages.", result["extracted_text"])
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["page_count"], 6)  # Should get the page count from async process

        # Verify that the stubbers were used correctly
        self.s3_stubber.assert_no_pending_responses()
        self.textract_stubber.assert_no_pending_responses()
        
    def test_process_document_async(self):
        """
        Test the process_document_async function.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "large-sample.pdf"
        job_id = "123456789"
        
        # Mock the start_document_text_detection response
        self.textract_stubber.add_response(
            "start_document_text_detection",
            {"JobId": job_id},
            {
                "DocumentLocation": {
                    "S3Object": {"Bucket": bucket_name, "Name": file_key}
                }
            }
        )
        
        # Mock the get_document_text_detection response for job status check
        self.textract_stubber.add_response(
            "get_document_text_detection",
            {
                "JobStatus": "SUCCEEDED",
                "DocumentMetadata": {"Pages": 3}
            },
            {"JobId": job_id}
        )
        
        # Mock the get_document_text_detection response for first page
        self.textract_stubber.add_response(
            "get_document_text_detection",
            {
                "JobStatus": "SUCCEEDED",
                "DocumentMetadata": {"Pages": 3},
                "Blocks": [
                    {
                        "BlockType": "LINE",
                        "Text": "First page text.",
                        "Id": "1",
                        "Confidence": 99.0
                    }
                ],
                "NextToken": "page2token"
            },
            {"JobId": job_id}
        )
        
        # Mock the get_document_text_detection response for second page
        self.textract_stubber.add_response(
            "get_document_text_detection",
            {
                "JobStatus": "SUCCEEDED",
                "Blocks": [
                    {
                        "BlockType": "LINE",
                        "Text": "Second page text.",
                        "Id": "2",
                        "Confidence": 98.0
                    }
                ],
                "NextToken": "page3token"
            },
            {"JobId": job_id, "NextToken": "page2token"}
        )
        
        # Mock the get_document_text_detection response for third page
        self.textract_stubber.add_response(
            "get_document_text_detection",
            {
                "JobStatus": "SUCCEEDED",
                "Blocks": [
                    {
                        "BlockType": "LINE",
                        "Text": "Third page text.",
                        "Id": "3",
                        "Confidence": 97.0
                    }
                ]
                # No NextToken means this is the last page
            },
            {"JobId": job_id, "NextToken": "page3token"}
        )
        
        # Activate the stubber
        self.textract_stubber.activate()
        
        # Call the function
        extracted_text, page_count = process_document_async(bucket_name, file_key)
        
        # Verify results
        self.assertEqual(page_count, 3)
        self.assertIn("First page text.", extracted_text)
        self.assertIn("Second page text.", extracted_text)
        self.assertIn("Third page text.", extracted_text)
        
        # Verify that the stubber was used correctly
        self.textract_stubber.assert_no_pending_responses()
    
    def test_process_document_async_timeout(self):
        """
        Test the process_document_async function when the job times out.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "timeout-sample.pdf"
        job_id = "timeout-job"
        
        # Mock the start_document_text_detection response
        self.textract_stubber.add_response(
            "start_document_text_detection",
            {"JobId": job_id},
            {
                "DocumentLocation": {
                    "S3Object": {"Bucket": bucket_name, "Name": file_key}
                }
            }
        )
        
        # Mock multiple IN_PROGRESS responses to simulate timeout
        # We'll use the same response multiple times
        for _ in range(20):  # Match max_tries in the handler
            self.textract_stubber.add_response(
                "get_document_text_detection",
                {
                    "JobStatus": "IN_PROGRESS"
                },
                {"JobId": job_id}
            )
        
        # Activate the stubber
        self.textract_stubber.activate()
        
        # Call the function and expect a timeout exception
        with self.assertRaises(Exception) as context:
            process_document_async(bucket_name, file_key)
        
        # Verify the exception message contains "timed out"
        self.assertIn("timed out", str(context.exception))
        
        # Verify that the stubber was used correctly
        self.textract_stubber.assert_no_pending_responses()
    
    def test_process_document_async_failed(self):
        """
        Test the process_document_async function when the job fails.
        """
        # Define test data
        bucket_name = "test-bucket"
        file_key = "failed-sample.pdf"
        job_id = "failed-job"
        
        # Mock the start_document_text_detection response
        self.textract_stubber.add_response(
            "start_document_text_detection",
            {"JobId": job_id},
            {
                "DocumentLocation": {
                    "S3Object": {"Bucket": bucket_name, "Name": file_key}
                }
            }
        )
        
        # Mock a FAILED response
        self.textract_stubber.add_response(
            "get_document_text_detection",
            {
                "JobStatus": "FAILED"
            },
            {"JobId": job_id}
        )
        
        # Activate the stubber
        self.textract_stubber.activate()
        
        # Call the function and expect a failure exception
        with self.assertRaises(Exception) as context:
            process_document_async(bucket_name, file_key)
        
        # Verify the exception message contains "failed"
        self.assertIn("failed", str(context.exception))
        
        # Verify that the stubber was used correctly
        self.textract_stubber.assert_no_pending_responses()

    def test_lambda_handler_with_exception(self):
        """
        Test the lambda_handler function when an exception occurs.
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

        # Call the lambda handler
        response = lambda_handler(event, {})

        # Verify the response
        self.assertEqual(response["statusCode"], 500)
        self.assertIn("message", response["body"])
        self.assertIn("Error extracting text from PDFs", response["body"]["message"])

        # Verify that the stubber was used correctly
        self.s3_stubber.assert_no_pending_responses()


if __name__ == "__main__":
    unittest.main()
