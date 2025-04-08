import json
import unittest
from unittest import mock
from datetime import datetime
import boto3
from botocore.stub import Stubber

# Import the Lambda handler
from src.lambda_functions.text_extractor.handler import lambda_handler, extract_text_from_pdf

class TestTextExtractorHandler(unittest.TestCase):
    """
    Test cases for the text_extractor Lambda function.
    """
    
    def setUp(self):
        """
        Set up test fixtures before each test.
        """
        # Create a mock S3 client
        self.s3_client = boto3.client('s3', region_name='us-east-1')
        self.s3_stubber = Stubber(self.s3_client)
        
        # Create a patcher for the boto3 client within the handler module
        self.s3_client_patch = mock.patch('src.lambda_functions.text_extractor.handler.s3_client', self.s3_client)
        self.s3_client_patch.start()
        
    def tearDown(self):
        """
        Clean up resources after each test.
        """
        # Stop the patcher
        self.s3_client_patch.stop()
        
    def test_extract_text_from_pdf(self):
        """
        Test the extract_text_from_pdf function.
        """
        # Define test data
        bucket_name = 'test-bucket'
        file_key = 'sample.pdf'
        content_length = 12345
        last_modified = datetime.now()
        
        # Stub the head_object method to return our test data
        self.s3_stubber.add_response(
            'head_object',
            {
                'ContentLength': content_length,
                'LastModified': last_modified,
                'ContentType': 'application/pdf'
            },
            {'Bucket': bucket_name, 'Key': file_key}
        )
        
        # Activate the stubber
        self.s3_stubber.activate()
        
        # Call the function
        result = extract_text_from_pdf(bucket_name, file_key)
        
        # Verify the result
        self.assertEqual(result['source']['bucket'], bucket_name)
        self.assertEqual(result['source']['file_key'], file_key)
        self.assertEqual(result['source']['size_bytes'], content_length)
        self.assertIn('extracted_text', result)
        self.assertEqual(result['status'], 'success')
        
        # Verify that the stubber was used correctly
        self.s3_stubber.assert_no_pending_responses()
        
    def test_lambda_handler_with_valid_event(self):
        """
        Test the lambda_handler function with a valid S3 event.
        """
        # Define test data
        bucket_name = 'test-bucket'
        file_key = 'sample.pdf'
        content_length = 12345
        last_modified = datetime.now()
        
        # Create a mock S3 event
        event = {
            'Records': [
                {
                    'eventSource': 'aws:s3',
                    's3': {
                        'bucket': {'name': bucket_name},
                        'object': {'key': file_key}
                    }
                }
            ]
        }
        
        # Stub the head_object method to return our test data
        self.s3_stubber.add_response(
            'head_object',
            {
                'ContentLength': content_length,
                'LastModified': last_modified,
                'ContentType': 'application/pdf'
            },
            {'Bucket': bucket_name, 'Key': file_key}
        )
        
        # Activate the stubber
        self.s3_stubber.activate()
        
        # Call the lambda handler
        response = lambda_handler(event, {})
        
        # Verify the response
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('message', response['body'])
        self.assertIn('results', response['body'])
        self.assertEqual(len(response['body']['results']), 1)
        
        # Verify that the stubber was used correctly
        self.s3_stubber.assert_no_pending_responses()
        
    def test_lambda_handler_with_non_pdf_file(self):
        """
        Test the lambda_handler function with a non-PDF file.
        """
        # Define test data
        bucket_name = 'test-bucket'
        file_key = 'sample.txt'
        
        # Create a mock S3 event
        event = {
            'Records': [
                {
                    'eventSource': 'aws:s3',
                    's3': {
                        'bucket': {'name': bucket_name},
                        'object': {'key': file_key}
                    }
                }
            ]
        }
        
        # Call the lambda handler
        response = lambda_handler(event, {})
        
        # Verify the response
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('message', response['body'])
        self.assertIn('results', response['body'])
        self.assertEqual(len(response['body']['results']), 0)
        
    def test_lambda_handler_with_no_records(self):
        """
        Test the lambda_handler function with an event that has no records.
        """
        # Create a mock S3 event with no records
        event = {'Records': []}
        
        # Call the lambda handler
        response = lambda_handler(event, {})
        
        # Verify the response
        self.assertEqual(response['statusCode'], 200)
        self.assertIn('message', response['body'])
        self.assertIn('results', response['body'])
        self.assertEqual(len(response['body']['results']), 0)

if __name__ == '__main__':
    unittest.main()