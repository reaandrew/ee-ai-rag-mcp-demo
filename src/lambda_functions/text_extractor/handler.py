import json
import boto3
import logging
import time
import os
import re
import secrets
from urllib.parse import unquote_plus

# Constants
CONTENT_TYPE_PLAIN = "text/plain"

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 and Textract clients with region from environment
# AWS Lambda environment has AWS_REGION variable, but we provide a default for local testing
region = os.environ.get("AWS_REGION", "eu-west-2")
logger.info(f"Using AWS region: {region}")
s3_client = boto3.client("s3", region_name=region)
textract_client = boto3.client("textract", region_name=region)

# Get environment variables
EXTRACTED_TEXT_BUCKET = os.environ.get("EXTRACTED_TEXT_BUCKET", "ee-ai-rag-mcp-demo-extracted-text")
EXTRACTED_TEXT_PREFIX = os.environ.get("EXTRACTED_TEXT_PREFIX", "ee-ai-rag-mcp-demo")
DELETE_ORIGINAL_PDF = os.environ.get("DELETE_ORIGINAL_PDF", "true").lower() == "true"


def check_for_existing_extraction(file_key):
    """
    Check if we already have an extracted text file for this PDF.

    Args:
        file_key (str): Key of the PDF file in S3

    Returns:
        tuple: (exists, txt_key) - Boolean if file exists and its key
    """
    # Create the expected target key for the extracted text
    filename = os.path.basename(file_key)
    txt_filename = re.sub(r"\.pdf$", ".txt", filename, flags=re.IGNORECASE)
    target_key = f"{EXTRACTED_TEXT_PREFIX}/{txt_filename}"

    try:
        # Check if the file exists
        s3_client.head_object(Bucket=EXTRACTED_TEXT_BUCKET, Key=target_key)
        logger.info(f"Found existing extracted text at {EXTRACTED_TEXT_BUCKET}/{target_key}")
        return True, target_key
    except Exception:
        # File doesn't exist
        return False, target_key


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
        # Check if we already have this file extracted
        text_exists, target_key = check_for_existing_extraction(file_key)
        if text_exists:
            logger.info(f"Skipping extraction for {file_key} - already processed")
            # Get metadata and return info about existing file
            obj = s3_client.get_object(Bucket=EXTRACTED_TEXT_BUCKET, Key=target_key)
            extracted_text = obj["Body"].read().decode("utf-8")

            # Count pages based on page markers in the text
            page_count = extracted_text.count("--- PAGE")

            return {
                "source": {
                    "bucket": bucket_name,
                    "file_key": file_key,
                },
                "output": {
                    "bucket": EXTRACTED_TEXT_BUCKET,
                    "file_key": target_key,
                    "size_bytes": len(extracted_text),
                    "content_type": CONTENT_TYPE_PLAIN,
                },
                "extracted_text": extracted_text,
                "page_count": page_count,
                "status": "success (cached)",
                "original_deleted": False,
            }

        # Get the object metadata
        metadata = s3_client.head_object(Bucket=bucket_name, Key=file_key)

        # Always use the asynchronous API for PDF processing
        # Synchronous API doesn't support PDF format
        logger.info(f"Using asynchronous Textract API for {file_key}")
        extracted_text, page_count = process_document_async(bucket_name, file_key)

        # Save the extracted text to the destination bucket
        # Create the target key by replacing the .pdf extension with .txt
        filename = os.path.basename(file_key)
        txt_filename = re.sub(r"\.pdf$", ".txt", filename, flags=re.IGNORECASE)
        target_key = f"{EXTRACTED_TEXT_PREFIX}/{txt_filename}"

        logger.info(f"Saving extracted text to {EXTRACTED_TEXT_BUCKET}/{target_key}")
        s3_client.put_object(
            Bucket=EXTRACTED_TEXT_BUCKET,
            Key=target_key,
            Body=extracted_text,
            ContentType=CONTENT_TYPE_PLAIN,
        )

        # Delete the original PDF if configured to do so
        original_deleted = False
        if DELETE_ORIGINAL_PDF:
            try:
                logger.info(f"Deleting original PDF from {bucket_name}/{file_key}")
                delete_response = s3_client.delete_object(Bucket=bucket_name, Key=file_key)
                logger.info(f"Delete API response: {delete_response}")

                # Verify deletion by trying to head the object
                try:
                    s3_client.head_object(Bucket=bucket_name, Key=file_key)
                    logger.warning(
                        f"PDF file still exists after deletion attempt: {bucket_name}/{file_key}"
                    )
                    original_deleted = False
                except Exception as head_error:
                    error_msg = str(head_error)
                    if any(x in error_msg for x in ["Not Found", "404", "NoSuchKey"]):
                        logger.info(
                            f"Verified deletion - PDF no longer exists: {bucket_name}/{file_key}"
                        )
                        original_deleted = True
                    else:
                        logger.warning(f"Error checking if PDF was deleted: {error_msg}")
                        original_deleted = False
            except Exception as delete_error:
                logger.error(f"Error deleting PDF {file_key}: {str(delete_error)}")
                original_deleted = False

        extraction_result = {
            "source": {
                "bucket": bucket_name,
                "file_key": file_key,
                "size_bytes": metadata.get("ContentLength", 0),
                "last_modified": str(metadata.get("LastModified", "")),
                "content_type": metadata.get("ContentType", "application/pdf"),
            },
            "output": {
                "bucket": EXTRACTED_TEXT_BUCKET,
                "file_key": target_key,
                "size_bytes": len(extracted_text),
                "content_type": CONTENT_TYPE_PLAIN,
            },
            "extracted_text": extracted_text,
            "page_count": page_count,
            "status": "success",
            "original_deleted": original_deleted,
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
    # Start the asynchronous document text detection with exponential backoff
    max_retries = 10
    base_delay = 1  # Base delay in seconds
    job_id = None
    for attempt in range(max_retries):
        try:
            response = textract_client.start_document_text_detection(
                DocumentLocation={"S3Object": {"Bucket": bucket_name, "Name": file_key}}
            )
            job_id = response["JobId"]
            logger.info(f"Started async Textract job {job_id} for {file_key}")
            break  # Success, exit retry loop
        except textract_client.exceptions.ProvisionedThroughputExceededException:
            # Calculate exponential backoff delay with secure jitter
            jitter = secrets.randbelow(200) / 100  # generates value between 0.0 and 1.99
            delay = min(30, (2**attempt) * base_delay + (2 * base_delay * jitter))
            if attempt < max_retries - 1:  # Don't log on the last attempt
                logger.warning(
                    f"Textract rate limit exceeded. Retrying in {delay:.2f}s. "
                    f"Attempt {attempt+1}/{max_retries}"
                )
                time.sleep(delay)
            else:
                logger.error(
                    f"Textract rate limit exceeded after {max_retries} attempts. Giving up."
                )
                raise
        except Exception as e:
            logger.error(f"Unexpected error starting Textract job: {str(e)}")
            raise
    if not job_id:
        raise Exception("Failed to start Textract job after retries")

    # Wait for the job to complete
    status = "IN_PROGRESS"
    max_tries = 60  # Allow up to 5 minutes polling time (60 * 5 = 300 seconds)
    wait_seconds = 5
    total_tries = 0

    while status == "IN_PROGRESS" and total_tries < max_tries:
        total_tries += 1
        try:
            # Add retry logic for get_document_text_detection with more retries
            retry_count = 0
            max_get_retries = 15  # Increased from 5 to 15 for higher throughput scenarios
            while retry_count < max_get_retries:
                try:
                    response = textract_client.get_document_text_detection(JobId=job_id)
                    break  # Success, exit retry loop
                except textract_client.exceptions.ProvisionedThroughputExceededException:
                    retry_count += 1
                    if retry_count >= max_get_retries:
                        logger.error("Rate limit exceeded when getting document text detection")
                        raise
                    # Enhanced exponential backoff with secure jitter
                    jitter = secrets.randbelow(200) / 100  # generates value between 0.0 and 1.99
                    # Increased base delay and max delay
                    delay = min(60, (2**retry_count) * 1.0 + jitter)
                    logger.warning(
                        f"Rate limit getting results. Retrying in {delay:.2f}s. "
                        f"Attempt {retry_count}/{max_get_retries}"
                    )
                    time.sleep(delay)
                except Exception as e:
                    logger.error(f"Error getting Textract results: {str(e)}")
                    raise
            status = response["JobStatus"]

            if status == "SUCCEEDED":
                break

            if status == "FAILED":
                error_message = "No error details available"
                if "StatusMessage" in response:
                    error_message = response["StatusMessage"]
                raise Exception(f"Textract job failed for {file_key}: {error_message}")

            logger.info(
                f"Textract job {job_id} is {status}. "
                f"Try {total_tries}/{max_tries}. Waiting {wait_seconds} seconds..."
            )
            time.sleep(wait_seconds)

        except Exception as e:
            logger.error(f"Error checking Textract job status: {str(e)}")
            raise e

    if total_tries >= max_tries and status == "IN_PROGRESS":
        seconds_waited = total_tries * wait_seconds
        error_msg = f"Textract job timed out after {seconds_waited} seconds "
        error_msg += f"(max timeout: {max_tries * wait_seconds} seconds)"
        job_msg = f" for job {job_id}. Job may still complete but Lambda timeout reached."
        logger.warning(error_msg + job_msg)
        # Instead of raising an exception, we'll store the job ID for future retrieval
        # Create an empty text file with the job ID to process later
        empty_text = (
            f"INCOMPLETE_TEXTRACT_JOB: {job_id}\n"
            f"File: {file_key}\n"
            f"Timeout after {seconds_waited} seconds"
        )
        return empty_text, 0

    # Get the results
    extracted_text = ""
    # Format for storing page info in the extracted text
    page_delimiter = "\n--- PAGE {page_num} ---\n"
    page_count = 0
    next_token = None
    current_page = 1

    while True:
        # Add retry logic for getting results with exponential backoff and increased retries
        retry_count = 0
        max_get_retries = 15  # Increased from 5 to 15 for higher throughput scenarios
        success = False
        while not success and retry_count < max_get_retries:
            try:
                if next_token:
                    response = textract_client.get_document_text_detection(
                        JobId=job_id, NextToken=next_token
                    )
                else:
                    response = textract_client.get_document_text_detection(JobId=job_id)
                success = True
            except textract_client.exceptions.ProvisionedThroughputExceededException:
                retry_count += 1
                if retry_count >= max_get_retries:
                    logger.error("Rate limit exceeded when getting document text detection")
                    raise
                # Enhanced exponential backoff with secure jitter
                jitter = secrets.randbelow(200) / 100  # generates value between 0.0 and 1.99
                # Increased base delay and max delay
                delay = min(60, (2**retry_count) * 1.0 + jitter)
                logger.warning(
                    f"Rate limit getting results. Retrying in {delay:.2f}s. "
                    f"Attempt {retry_count}/{max_get_retries}"
                )
                time.sleep(delay)
            except Exception as e:
                logger.error(f"Error getting Textract results: {str(e)}")
                raise
        if not success:
            raise Exception("Failed to get Textract results after multiple retries")

        # Update the page count
        # Each page in the response increases the DocumentMetadata.Pages count
        if "DocumentMetadata" in response:
            page_count = response["DocumentMetadata"]["Pages"]

        # Process blocks, tracking page changes
        for item in response["Blocks"]:
            if item["BlockType"] == "LINE":
                # Check if this is a new page
                block_page = item.get("Page", current_page)
                if block_page > current_page:
                    # Add page delimiter before starting new page content
                    extracted_text += page_delimiter.format(page_num=block_page)
                    current_page = block_page

                # Add the line of text
                extracted_text += item["Text"] + "\n"

        # Check if there are more pages to process
        if "NextToken" in response:
            next_token = response["NextToken"]
        else:
            break

    # Ensure the page delimiter is at the start of the first page
    if extracted_text and not extracted_text.startswith("--- PAGE 1 ---"):
        extracted_text = page_delimiter.format(page_num=1) + extracted_text

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
