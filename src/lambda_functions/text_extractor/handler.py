import json
import boto3
import logging
from urllib.parse import unquote_plus

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client
s3_client = boto3.client("s3")


def extract_text_from_pdf(bucket_name, file_key):
    """
    Extract text from a PDF file in S3.

    Args:
        bucket_name (str): Name of the S3 bucket
        file_key (str): Key of the PDF file in S3

    Returns:
        dict: Information about the extracted text and metadata
    """
    logger.info(f"Extracting text from PDF: {file_key} in bucket {bucket_name}")

    try:
        # Get the object metadata
        metadata = s3_client.head_object(Bucket=bucket_name, Key=file_key)

        # In a real implementation, we would download the file and use a PDF extraction
        # library like PyPDF2, pdf2image + pytesseract, or textract. For this demo,
        # we'll just return placeholder information.

        extraction_result = {
            "source": {
                "bucket": bucket_name,
                "file_key": file_key,
                "size_bytes": metadata.get("ContentLength", 0),
                "last_modified": str(metadata.get("LastModified", "")),
                "content_type": metadata.get("ContentType", "application/pdf"),
            },
            # This would be the actual extracted text
            "extracted_text": f"Placeholder text for {file_key}",
            "page_count": 1,  # This would be determined from the PDF
            "status": "success",
        }

        logger.info(f"Successfully extracted text from {file_key}")
        return extraction_result

    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_key}: {str(e)}")
        raise e


def lambda_handler(event, context):
    """
    Lambda function handler that processes S3 object creation events.

    Args:
        event (dict): Event data from S3
        context (LambdaContext): Lambda context

    Returns:
        dict: Response with text extraction results
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Process each record in the S3 event
        results = []
        for record in event.get("Records", []):
            # Check if this is an S3 event
            if record.get("eventSource") != "aws:s3":
                continue

            # Get S3 bucket and file information
            bucket_name = record.get("s3", {}).get("bucket", {}).get("name")
            file_key = unquote_plus(record.get("s3", {}).get("object", {}).get("key"))

            # Only process PDF files
            if not file_key.lower().endswith(".pdf"):
                logger.info(f"Skipping non-PDF file: {file_key}")
                continue

            # Extract text from the PDF
            result = extract_text_from_pdf(bucket_name, file_key)
            results.append(result)

        # Return the results
        response = {
            "statusCode": 200,
            "body": {
                "message": f"Extracted text from {len(results)} PDF files",
                "results": results,
            },
        }

        return response

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"message": f"Error extracting text from PDFs: {str(e)}"},
        }
