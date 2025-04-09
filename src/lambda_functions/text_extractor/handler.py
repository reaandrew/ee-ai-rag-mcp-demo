import json
import boto3
import logging
import time
import os
import re
from urllib.parse import unquote_plus

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 and Textract clients with default region
# AWS Lambda environment has region configuration, but for local testing we set a default
default_region = "eu-west-2"  # Match the region in Terraform config
s3_client = boto3.client("s3", region_name=default_region)
textract_client = boto3.client("textract", region_name=default_region)

# Get environment variables
EXTRACTED_TEXT_BUCKET = os.environ.get("EXTRACTED_TEXT_BUCKET", "ee-ai-rag-mcp-demo-extracted-text")
EXTRACTED_TEXT_PREFIX = os.environ.get("EXTRACTED_TEXT_PREFIX", "ee-ai-rag-mcp-demo")
DELETE_ORIGINAL_PDF = os.environ.get("DELETE_ORIGINAL_PDF", "true").lower() == "true"


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
            ContentType="text/plain",
        )

        # Delete the original PDF if configured to do so
        if DELETE_ORIGINAL_PDF:
            logger.info(f"Deleting original PDF from {bucket_name}/{file_key}")
            s3_client.delete_object(Bucket=bucket_name, Key=file_key)

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
                "content_type": "text/plain",
            },
            "extracted_text": extracted_text,
            "page_count": page_count,
            "status": "success",
            "original_deleted": DELETE_ORIGINAL_PDF,
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
    max_tries = 30  # Allow up to 2.5 minutes polling time (30 * 5 = 150 seconds)
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
        error_msg += "(max timeout: 150 seconds)"
        raise Exception(error_msg)

    # Get the results
    extracted_text = ""
    # Format for storing page info in the extracted text
    page_delimiter = "\n--- PAGE {page_num} ---\n"
    page_count = 0
    next_token = None
    current_page = 1

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
