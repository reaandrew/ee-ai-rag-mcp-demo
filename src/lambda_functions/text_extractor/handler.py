import json
import boto3
import logging
import time
from urllib.parse import unquote_plus

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 and Textract clients with default region
# AWS Lambda environment has region configuration, but for local testing we set a default
default_region = "eu-west-2"  # Match the region in Terraform config
s3_client = boto3.client("s3", region_name=default_region)
textract_client = boto3.client("textract", region_name=default_region)


def extract_text_from_pdf(bucket_name, file_key):
    """
    Extract text from a PDF file in S3 using AWS Textract.

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

        # For PDFs with fewer pages (<=5), we can use the synchronous API
        # For larger PDFs, use the asynchronous API

        # 1. First try the synchronous API with DetectDocumentText
        try:
            logger.info(f"Using synchronous Textract API for {file_key}")
            response = textract_client.detect_document_text(
                Document={"S3Object": {"Bucket": bucket_name, "Name": file_key}}
            )

            # Extract text blocks from the response
            extracted_text = ""
            for item in response["Blocks"]:
                if item["BlockType"] == "LINE":
                    extracted_text += item["Text"] + "\n"

            page_count = 1  # Synchronous API doesn't provide page count

        except textract_client.exceptions.InvalidParameterException as e:
            # The PDF may be too large for synchronous processing
            # Fall back to asynchronous processing
            error_message = str(e)
            if "Page limit" in error_message:
                logger.info(
                    f"PDF {file_key} is too large for synchronous processing. Using async API."
                )
                extracted_text, page_count = process_document_async(bucket_name, file_key)
            else:
                logger.error(f"Unhandled InvalidParameterException: {error_message}")
                raise e

        extraction_result = {
            "source": {
                "bucket": bucket_name,
                "file_key": file_key,
                "size_bytes": metadata.get("ContentLength", 0),
                "last_modified": str(metadata.get("LastModified", "")),
                "content_type": metadata.get("ContentType", "application/pdf"),
            },
            "extracted_text": extracted_text,
            "page_count": page_count,
            "status": "success",
        }

        logger.info(f"Successfully extracted text from {file_key}")
        return extraction_result

    except Exception as e:
        logger.error(f"Error extracting text from PDF {file_key}: {str(e)}")
        raise e


def process_document_async(bucket_name, file_key):
    """
    Process a document asynchronously using Textract.

    Args:
        bucket_name (str): The S3 bucket name
        file_key (str): The S3 object key

    Returns:
        tuple: (extracted_text, page_count)
    """
    # Start the asynchronous document text detection
    response = textract_client.start_document_text_detection(
        DocumentLocation={"S3Object": {"Bucket": bucket_name, "Name": file_key}}
    )

    job_id = response["JobId"]
    logger.info(f"Started async Textract job {job_id} for {file_key}")

    # Wait for the job to complete
    status = "IN_PROGRESS"
    max_tries = 12  # Adjust for 1 minute timeout (12 * 5 = 60 seconds)
    wait_seconds = 5
    total_tries = 0

    while status == "IN_PROGRESS" and total_tries < max_tries:
        total_tries += 1
        try:
            response = textract_client.get_document_text_detection(JobId=job_id)
            status = response["JobStatus"]

            if status == "SUCCEEDED":
                break

            if status == "FAILED":
                raise Exception(f"Textract job failed for {file_key}")

            logger.info(f"Textract job {job_id} is {status}. Waiting {wait_seconds} seconds...")
            time.sleep(wait_seconds)

        except Exception as e:
            logger.error(f"Error checking Textract job status: {str(e)}")
            raise e

    if total_tries >= max_tries and status == "IN_PROGRESS":
        seconds_waited = total_tries * wait_seconds
        error_msg = f"Textract job timed out after {seconds_waited} seconds "
        error_msg += "(max timeout: 60 seconds)"
        raise Exception(error_msg)

    # Get the results
    extracted_text = ""
    page_count = 0
    next_token = None

    while True:
        if next_token:
            response = textract_client.get_document_text_detection(
                JobId=job_id, NextToken=next_token
            )
        else:
            response = textract_client.get_document_text_detection(JobId=job_id)

        # Update the page count
        # Each page in the response increases the DocumentMetadata.Pages count
        if "DocumentMetadata" in response:
            page_count = response["DocumentMetadata"]["Pages"]

        # Extract text from blocks
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                extracted_text += item["Text"] + "\n"

        # Check if there are more pages to process
        if "NextToken" in response:
            next_token = response["NextToken"]
        else:
            break

    msg = (
        f"Completed async Textract job {job_id}. "
        f"Extracted {len(extracted_text)} chars from {page_count} pages."
    )
    logger.info(msg)
    return extracted_text, page_count


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
