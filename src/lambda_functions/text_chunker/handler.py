import json
import boto3
import logging
import os
from urllib.parse import unquote_plus
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client with default region
# AWS Lambda environment has region configuration, but for local testing we set a default
default_region = "eu-west-2"  # Match the region in Terraform config
s3_client = boto3.client("s3", region_name=default_region)

# Get environment variables
CHUNKED_TEXT_BUCKET = os.environ.get("CHUNKED_TEXT_BUCKET", "ee-ai-rag-mcp-demo-chunked-text")
CHUNKED_TEXT_PREFIX = os.environ.get("CHUNKED_TEXT_PREFIX", "ee-ai-rag-mcp-demo")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "200"))


def chunk_text(text, metadata=None):
    """
    Split text into chunks using RecursiveCharacterTextSplitter.

    Args:
        text (str): The text to chunk
        metadata (dict, optional): Additional metadata to include with chunks

    Returns:
        list: A list of dictionaries containing chunks and metadata
    """
    logger.info(f"Chunking text of length {len(text)} characters")

    # Create a text splitter with the specified configuration
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    # Split the text into chunks
    chunks = text_splitter.split_text(text)
    logger.info(f"Created {len(chunks)} chunks")

    # Prepare the result with metadata
    result = []
    for i, chunk in enumerate(chunks):
        chunk_info = {
            "chunk_id": i,
            "total_chunks": len(chunks),
            "text": chunk,
            "chunk_size": len(chunk),
        }

        # Add the provided metadata if available
        if metadata:
            chunk_info["metadata"] = metadata

        result.append(chunk_info)

    return result


def process_text_file(bucket_name, file_key):
    """
    Process a text file from S3, chunk it, and save chunks to the destination bucket.

    Args:
        bucket_name (str): Name of the S3 bucket containing the text file
        file_key (str): Key of the text file in S3

    Returns:
        dict: Information about the chunking operation
    """
    logger.info(f"Processing text file: {file_key} in bucket {bucket_name}")

    try:
        # Get the object metadata
        metadata = s3_client.head_object(Bucket=bucket_name, Key=file_key)

        # Get the text content
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        text_content = response["Body"].read().decode("utf-8")

        # Extract filename without extension for use in output
        filename = os.path.basename(file_key)
        filename_without_ext = os.path.splitext(filename)[0]

        # Prepare metadata for chunks
        file_metadata = {
            "source_bucket": bucket_name,
            "source_key": file_key,
            "filename": filename,
            "content_type": metadata.get("ContentType", "text/plain"),
            "last_modified": str(metadata.get("LastModified", "")),
            "size_bytes": metadata.get("ContentLength", 0),
        }

        # Chunk the text
        chunks = chunk_text(text_content, file_metadata)

        # Save each chunk to S3
        saved_chunks = []
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            chunk_key = f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/chunk_{chunk_id}.json"

            # Save the chunk as JSON
            s3_client.put_object(
                Bucket=CHUNKED_TEXT_BUCKET,
                Key=chunk_key,
                Body=json.dumps(chunk, ensure_ascii=False),
                ContentType="application/json",
            )

            saved_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "key": chunk_key,
                    "size": len(json.dumps(chunk, ensure_ascii=False)),
                }
            )

        # Create a manifest file with summary information
        manifest = {
            "source": file_metadata,
            "chunking": {
                "total_chunks": len(chunks),
                "chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
                "chunks": saved_chunks,
            },
            "output": {
                "bucket": CHUNKED_TEXT_BUCKET,
                "prefix": f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/",
            },
        }

        # Save the manifest
        manifest_key = f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/manifest.json"
        s3_client.put_object(
            Bucket=CHUNKED_TEXT_BUCKET,
            Key=manifest_key,
            Body=json.dumps(manifest, ensure_ascii=False),
            ContentType="application/json",
        )

        logger.info(f"Successfully processed and chunked {file_key} into {len(chunks)} chunks")
        return {
            "source": {
                "bucket": bucket_name,
                "file_key": file_key,
            },
            "output": {
                "bucket": CHUNKED_TEXT_BUCKET,
                "manifest_key": manifest_key,
                "total_chunks": len(chunks),
            },
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error processing text file {file_key}: {str(e)}")
        raise e


def lambda_handler(event, context):
    """
    Lambda function handler that processes S3 object creation events.

    Args:
        event (dict): Event data from S3
        context (LambdaContext): Lambda context

    Returns:
        dict: Response with chunking results
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

            # Only process text files
            if not file_key.lower().endswith(".txt"):
                logger.info(f"Skipping non-text file: {file_key}")
                continue

            # Process the text file
            result = process_text_file(bucket_name, file_key)
            results.append(result)

        # Return the results
        response = {
            "statusCode": 200,
            "body": {
                "message": f"Processed and chunked {len(results)} text files",
                "results": results,
            },
        }

        return response

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"message": f"Error processing text files: {str(e)}"},
        }
