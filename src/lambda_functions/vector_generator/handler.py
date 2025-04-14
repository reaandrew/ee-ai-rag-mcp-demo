import json
import boto3
import logging
import os
from urllib.parse import unquote_plus

# datetime imported but used only in tracking_utils

try:
    # Try to import tracking utils
    from utils import tracking_utils
except ImportError:
    try:
        # When running locally or in tests with src structure
        from src.utils import tracking_utils
    except ImportError:
        try:
            # Absolute import (sometimes needed in Lambda)
            import utils.tracking_utils as tracking_utils
        except ImportError:
            # Define a fallback for tracking in case import fails
            tracking_utils = None
            logging.warning(
                "Could not import tracking_utils module, document tracking will be disabled"
            )

# Try to import from different locations depending on the context
try:
    # When running in the Lambda environment with utils copied locally
    from utils import opensearch_utils, bedrock_utils
except ImportError:
    try:
        # When running locally or in tests with src structure
        from src.utils import opensearch_utils, bedrock_utils
    except ImportError:
        try:
            # Absolute import (sometimes needed in Lambda)
            import utils.opensearch_utils as opensearch_utils
            import utils.bedrock_utils as bedrock_utils
        except ImportError:
            # All imports failed
            logging.error("Could not import utils modules from standard locations")
            raise

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use the Lambda runtime's AWS_REGION environment variable
# This is automatically set by the Lambda runtime
# Provide a fallback for testing environments where AWS_REGION might not be set
region = os.environ.get("AWS_REGION", "eu-west-2")

# Initialize AWS clients
s3_client = boto3.client("s3", region_name=region)

# Get environment variables
CHUNKED_TEXT_BUCKET = os.environ.get("CHUNKED_TEXT_BUCKET", "ee-ai-rag-mcp-demo-chunked-text")
OPENSEARCH_DOMAIN = os.environ.get("OPENSEARCH_DOMAIN", "ee-ai-rag-mcp-demo-vectors")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", None)  # From Terraform
OPENSEARCH_INDEX = os.environ.get("OPENSEARCH_INDEX", "rag-vectors")
VECTOR_PREFIX = os.environ.get("VECTOR_PREFIX", "ee-ai-rag-mcp-demo")
MODEL_ID = os.environ.get("MODEL_ID", "amazon.titan-embed-text-v2:0")

# Additional flags for authentication
USE_IAM_AUTH = os.environ.get("USE_IAM_AUTH", "true").lower() == "true"
USE_AOSS = os.environ.get("USE_AOSS", "false").lower() == "true"

# Create the OpenSearch client
opensearch_client = opensearch_utils.get_opensearch_client()


def create_index_if_not_exists():
    """
    Create OpenSearch index with embedding mapping if it doesn't exist.
    The index is configured with the appropriate mapping for vector search.
    """
    return opensearch_utils.create_index_if_not_exists(opensearch_client, OPENSEARCH_INDEX)


def generate_embedding(text):
    """
    Generate embeddings for the provided text using AWS Bedrock Titan.

    Args:
        text (str): The text to generate embeddings for

    Returns:
        list: The embedding vector
    """
    # Override the default model ID from the utility with our environment variable
    return bedrock_utils.generate_embedding(text, model_id=MODEL_ID)


def process_chunk_file(bucket_name, file_key):
    """
    Process a chunk file from S3, generate vector embeddings, and store in OpenSearch.

    Args:
        bucket_name (str): Name of the S3 bucket containing the chunk file
        file_key (str): Key of the chunk file in S3

    Returns:
        dict: Information about the vectorization operation
    """
    logger.info(f"Processing chunk file: {file_key} in bucket {bucket_name}")

    try:
        # Ensure OpenSearch index exists
        create_index_if_not_exists()

        # Get the object from S3
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        chunk_data = json.loads(response["Body"].read().decode("utf-8"))

        # Extract the text from the chunk
        text = chunk_data.get("text", "")
        if not text:
            raise ValueError(f"No text found in chunk file {file_key}")

        # Generate embedding for the text
        embedding = generate_embedding(text)

        # Create OpenSearch document from chunk data
        document = {
            "text": text,
            "embedding": embedding,
            "embedding_model": MODEL_ID,
            "embedding_dimension": len(embedding),
            "source_key": file_key,
            "document_name": chunk_data.get("document_name", ""),
            # Ensure page_number is a string for OpenSearch compatibility
            "page_number": str(chunk_data.get("page_number", "0")),
            "metadata": chunk_data.get("metadata", {}),
        }

        # Generate a document ID from the file key (make it deterministic)
        doc_id = file_key.replace("/", "_").replace(".", "_")

        # Index the document in OpenSearch if the client is available
        if opensearch_client:
            opensearch_response = opensearch_client.index(
                index=OPENSEARCH_INDEX,
                id=doc_id,
                body=document,
                refresh=True,  # Ensure document is searchable immediately
            )
            logger.info(f"Indexed document in OpenSearch: {opensearch_response}")

            # Update tracking information if available
            if tracking_utils:
                # Extract document_id from metadata
                document_id = chunk_data.get("metadata", {}).get("document_id")
                if document_id:
                    tracking_utils.update_indexing_progress(
                        document_id=document_id,
                        document_name=chunk_data.get("document_name", ""),
                        page_number=str(chunk_data.get("page_number", "0")),
                    )
                    logger.info(f"Updated tracking for document: {document_id}")
                else:
                    logger.warning("No document_id found in metadata, tracking not updated")
        else:
            logger.warning("OpenSearch client not available, skipping indexing")

        # Return information about the vectorization
        return {
            "source": {
                "bucket": bucket_name,
                "file_key": file_key,
            },
            "output": {
                "opensearch_domain": OPENSEARCH_DOMAIN,
                "opensearch_index": OPENSEARCH_INDEX,
                "document_id": doc_id,
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
