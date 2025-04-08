#!/usr/bin/env python3
"""
Script to invoke the text extractor Lambda function by uploading a PDF to S3.

This script:
1. Creates a sample PDF file if none is provided
2. Uploads the PDF to the S3 bucket
3. Invokes the Lambda function directly 
4. Displays the Lambda function response
"""

import argparse
import boto3
import json
import os
import time
import uuid
from botocore.exceptions import ClientError
from reportlab.pdfgen import canvas


def create_sample_pdf(output_path):
    """Create a simple PDF file for testing."""
    c = canvas.Canvas(output_path)
    c.drawString(100, 750, "Sample PDF for Lambda Text Extractor Testing")
    c.drawString(100, 700, f"Generated at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    c.drawString(100, 650, "This PDF was created to test the ee-ai-rag-mcp-demo text extractor Lambda.")
    c.drawString(100, 600, "It contains sample text that should be extracted by the Lambda function.")
    c.save()
    print(f"Created sample PDF: {output_path}")


def upload_file_to_s3(file_path, bucket_name, object_key=None):
    """Upload a file to an S3 bucket."""
    if object_key is None:
        object_key = os.path.basename(file_path)
    
    s3_client = boto3.client('s3')
    try:
        s3_client.upload_file(file_path, bucket_name, object_key)
        print(f"Successfully uploaded {file_path} to {bucket_name}/{object_key}")
        return True
    except ClientError as e:
        print(f"Error uploading file to S3: {e}")
        return False


def invoke_lambda_directly(function_name, event):
    """Invoke a Lambda function directly with an event."""
    lambda_client = boto3.client('lambda')
    try:
        response = lambda_client.invoke(
            FunctionName=function_name,
            InvocationType='RequestResponse',  # Synchronous invocation
            Payload=json.dumps(event)
        )
        
        payload = response['Payload'].read().decode('utf-8')
        status_code = response.get('StatusCode', 0)
        
        print(f"Lambda invocation status code: {status_code}")
        return json.loads(payload) if payload else None
    except ClientError as e:
        print(f"Error invoking Lambda function: {e}")
        return None


def create_s3_event(bucket_name, object_key):
    """Create a mock S3 event that simulates an object being created."""
    return {
        "Records": [
            {
                "eventVersion": "2.1",
                "eventSource": "aws:s3",
                "awsRegion": "us-east-1",
                "eventTime": time.strftime("%Y-%m-%dT%H:%M:%S.000Z"),
                "eventName": "ObjectCreated:Put",
                "userIdentity": {
                    "principalId": "AWS:AIDAJDPLRKLG7UEXAMPLE"
                },
                "requestParameters": {
                    "sourceIPAddress": "127.0.0.1"
                },
                "responseElements": {
                    "x-amz-request-id": str(uuid.uuid4()),
                    "x-amz-id-2": "EXAMPLE123/5678abcdefghijklambdaisawesome/mnopqrstuvwxyzABCDEFGH"
                },
                "s3": {
                    "s3SchemaVersion": "1.0",
                    "configurationId": "testConfigRule",
                    "bucket": {
                        "name": bucket_name,
                        "ownerIdentity": {
                            "principalId": "EXAMPLE"
                        },
                        "arn": f"arn:aws:s3:::{bucket_name}"
                    },
                    "object": {
                        "key": object_key,
                        "size": 1024,
                        "eTag": "0123456789abcdef0123456789abcdef",
                        "sequencer": "0A1B2C3D4E5F678901"
                    }
                }
            }
        ]
    }


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Invoke text extractor Lambda by uploading a PDF file to S3')
    
    parser.add_argument('--pdf', type=str, help='Path to a PDF file to upload (if not provided, a sample PDF will be created)')
    parser.add_argument('--bucket', type=str, required=True, help='S3 bucket name for raw PDFs')
    parser.add_argument('--lambda-name', type=str, default='ee-ai-rag-mcp-demo-text-extractor', 
                        help='Lambda function name (default: ee-ai-rag-mcp-demo-text-extractor)')
    parser.add_argument('--key', type=str, help='Object key in S3 (default: auto-generated)')
    
    return parser.parse_args()


def main():
    """Main function."""
    args = parse_arguments()
    
    # Create or use provided PDF
    pdf_path = args.pdf
    if not pdf_path:
        pdf_path = f"/tmp/sample_{int(time.time())}.pdf"
        create_sample_pdf(pdf_path)
    
    # Generate a unique key if not provided
    object_key = args.key
    if not object_key:
        file_basename = os.path.basename(pdf_path)
        timestamp = int(time.time())
        object_key = f"uploads/{timestamp}_{file_basename}"
    
    # Upload PDF to S3
    upload_success = upload_file_to_s3(pdf_path, args.bucket, object_key)
    if not upload_success:
        print("Failed to upload file. Exiting.")
        return
    
    # First approach: Lambda should be triggered automatically by S3 event notification
    print("\nThe Lambda function should be automatically triggered by the S3 event notification.")
    print("Waiting 5 seconds for the Lambda function to be invoked and complete processing...")
    time.sleep(5)
    
    # Second approach: Manually invoke Lambda with a simulated S3 event
    print("\nManually invoking Lambda with a simulated S3 event:")
    s3_event = create_s3_event(args.bucket, object_key)
    response = invoke_lambda_directly(args.lambda_name, s3_event)
    
    # Display the results
    if response:
        print("\nLambda Response:")
        print(json.dumps(response, indent=2))
    
    print("\nTest completed.")


if __name__ == "__main__":
    main()