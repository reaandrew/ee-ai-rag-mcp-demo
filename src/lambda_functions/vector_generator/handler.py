import json
import boto3
import logging
import os
from urllib.parse import unquote_plus

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client with default region
# AWS Lambda environment has region configuration, but for local testing we set a default
default_region = "eu-west-2"  # Match the region in Terraform config
s3_client = boto3.client("s3", region_name=default_region)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=default_region)

# Get environment variables
CHUNKED_TEXT_BUCKET = os.environ.get("CHUNKED_TEXT_BUCKET", "ee-ai-rag-mcp-demo-chunked-text")
VECTOR_BUCKET = os.environ.get("VECTOR_BUCKET", "ee-ai-rag-mcp-demo-vectors")
VECTOR_PREFIX = os.environ.get("VECTOR_PREFIX", "ee-ai-rag-mcp-demo")
MODEL_ID = os.environ.get("MODEL_ID", "amazon.titan-embed-text-v1")


def generate_embedding(text):
    """
    Generate embeddings for the provided text using AWS Bedrock Titan.

    Args:
        text (str): The text to generate embeddings for

    Returns:
        list: The embedding vector
    """
    try:
        # Prepare request body for Titan embedding model
        request_body = json.dumps({"inputText": text})

        # Call Bedrock to generate embeddings
        response = bedrock_runtime.invoke_model(modelId=MODEL_ID, body=request_body)

        # Parse response
        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding", [])

        logger.info(f"Successfully generated embedding with dimension {len(embedding)}")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise e


def process_chunk_file(bucket_name, file_key):
    """
    Process a chunk file from S3, generate vector embeddings, and save to the destination bucket.

    Args:
        bucket_name (str): Name of the S3 bucket containing the chunk file
        file_key (str): Key of the chunk file in S3

    Returns:
        dict: Information about the vectorization operation
    """
    logger.info(f"Processing chunk file: {file_key} in bucket {bucket_name}")

    try:
        # Get the object
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        chunk_data = json.loads(response["Body"].read().decode("utf-8"))

        # Extract the text from the chunk
        text = chunk_data.get("text", "")
        if not text:
            raise ValueError(f"No text found in chunk file {file_key}")

        # Generate embedding for the text
        embedding = generate_embedding(text)

        # Add the embedding to the chunk data
        chunk_data["embedding"] = embedding
        chunk_data["embedding_model"] = MODEL_ID
        chunk_data["embedding_dimension"] = len(embedding)

        # Create vector file key from chunk file key
        # Replace chunked_text prefix with vector prefix if needed
        vector_key = file_key.replace(".json", "_vector.json")

        # Ensure the correct prefix is used
        if VECTOR_PREFIX and not vector_key.startswith(VECTOR_PREFIX):
            # Extract filename from the chunk path (after the last slash)
            filename = file_key.split("/")[-1]
            # Get the path from the chunk (document name)
            doc_path = "/".join(file_key.split("/")[1:-1]) if "/" in file_key else ""

            if doc_path:
                vector_key = (
                    f"{VECTOR_PREFIX}/{doc_path}/{filename.replace('.json', '_vector.json')}"
                )
            else:
                vector_key = f"{VECTOR_PREFIX}/{filename.replace('.json', '_vector.json')}"

        # Save the vector data to S3
        s3_client.put_object(
            Bucket=VECTOR_BUCKET,
            Key=vector_key,
            Body=json.dumps(chunk_data, ensure_ascii=False),
            ContentType="application/json",
        )

        # Return information about the vectorization
        return {
            "source": {
                "bucket": bucket_name,
                "file_key": file_key,
            },
            "output": {
                "bucket": VECTOR_BUCKET,
                "vector_key": vector_key,
                "embedding_dimension": len(embedding),
                "model_id": MODEL_ID,
            },
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error processing chunk file {file_key}: {str(e)}")
        raise e


def lambda_handler(event, context):
    """
    Lambda function handler that processes S3 object creation events.

    Args:
        event (dict): Event data from S3
        context (LambdaContext): Lambda context

    Returns:
        dict: Response with vectorization results
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

            # Only process JSON files that are not vector files
            if not file_key.lower().endswith(".json") or file_key.lower().endswith("_vector.json"):
                logger.info(f"Skipping non-chunk file: {file_key}")
                continue

            # Skip manifest files
            if file_key.lower().endswith("manifest.json"):
                logger.info(f"Skipping manifest file: {file_key}")
                continue

            # Process the chunk file
            result = process_chunk_file(bucket_name, file_key)
            results.append(result)

        # Return the results
        response = {
            "statusCode": 200,
            "body": {
                "message": f"Processed and vectorized {len(results)} chunk files",
                "results": results,
            },
        }

        return response

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"message": f"Error processing chunk files: {str(e)}"},
        }
