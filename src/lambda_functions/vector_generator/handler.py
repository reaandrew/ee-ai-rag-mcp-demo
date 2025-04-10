import json
import boto3
import logging
import os
import time
from urllib.parse import unquote_plus
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use the Lambda runtime's AWS_REGION environment variable
# This is automatically set by the Lambda runtime
region = os.environ.get("AWS_REGION")

# Initialize AWS clients
s3_client = boto3.client("s3", region_name=region)
bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)

# Get environment variables
CHUNKED_TEXT_BUCKET = os.environ.get("CHUNKED_TEXT_BUCKET", "ee-ai-rag-mcp-demo-chunked-text")
OPENSEARCH_DOMAIN = os.environ.get("OPENSEARCH_DOMAIN", "ee-ai-rag-mcp-demo-vectors")
OPENSEARCH_INDEX = os.environ.get("OPENSEARCH_INDEX", "rag-vectors")
VECTOR_PREFIX = os.environ.get("VECTOR_PREFIX", "ee-ai-rag-mcp-demo")
MODEL_ID = os.environ.get("MODEL_ID", "amazon.titan-embed-text-v2:0")


# Get OpenSearch credentials from AWS Secrets Manager
def get_opensearch_credentials():
    """
    Retrieve OpenSearch credentials from AWS Secrets Manager.
    Returns a tuple of (username, password) or (None, None) if not found.
    """
    try:
        # Create a Secrets Manager client
        secrets_client = boto3.client("secretsmanager", region_name=region)

        # Get the secret value
        secret_name = "ee-ai-rag-mcp-demo/opensearch-master-credentials"
        response = secrets_client.get_secret_value(SecretId=secret_name)

        # Parse the secret JSON string
        secret = json.loads(response["SecretString"])
        return secret.get("username"), secret.get("password")

    except Exception as e:
        logger.warning(f"Could not retrieve OpenSearch credentials from Secrets Manager: {str(e)}")
        logger.warning("Will attempt to use IAM authentication instead")
        return None, None


# Initialize OpenSearch client with AWS authentication
def get_opensearch_client():
    """
    Create and return an OpenSearch client with proper AWS authentication.
    This is separated to make testing easier, as AWS credentials may not be
    available in test environments.
    """
    try:
        # First try to get credentials from Secrets Manager
        username, password = get_opensearch_credentials()

        # If we have username/password from Secrets Manager, use basic auth
        if username and password:
            logger.info(f"Using Secrets Manager credentials for user: {username}")
            return OpenSearch(
                hosts=[{"host": f"{OPENSEARCH_DOMAIN}.{region}.es.amazonaws.com", "port": 443}],
                http_auth=(username, password),
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
            )

        # Fall back to IAM authentication
        credentials = boto3.Session().get_credentials()
        if credentials:
            logger.info("Using IAM authentication for OpenSearch")
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                "es",
                session_token=credentials.token,
            )

            # Create OpenSearch client with AWS authentication
            return OpenSearch(
                hosts=[{"host": f"{OPENSEARCH_DOMAIN}.{region}.es.amazonaws.com", "port": 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
            )
        else:
            logger.warning("No authentication method available for OpenSearch")
            # In test environments, we might want to return a mock client
            return None

    except Exception as e:
        logger.error(f"Error creating OpenSearch client: {str(e)}")
        # In a test environment, we might still want to continue
        return None


# Create the OpenSearch client
opensearch_client = get_opensearch_client()


def create_index_if_not_exists():
    """
    Create OpenSearch index with embedding mapping if it doesn't exist.
    The index is configured with the appropriate mapping for vector search.
    """
    try:
        # Check if OpenSearch client is available
        if not opensearch_client:
            logger.warning("OpenSearch client not available, skipping index creation")
            return True

        # Check if index exists
        if not opensearch_client.indices.exists(index=OPENSEARCH_INDEX):
            logger.info(f"Creating OpenSearch index: {OPENSEARCH_INDEX}")

            # Define mappings for vector search
            index_body = {
                "settings": {
                    "index": {
                        "number_of_shards": 2,
                        "number_of_replicas": 1,
                        "knn": True,
                        "knn.algo_param.ef_search": 100,
                    }
                },
                "mappings": {
                    "properties": {
                        "embedding": {
                            "type": "knn_vector",
                            "dimension": 1536,  # Default dimension for Titan embeddings
                            "method": {
                                "name": "hnsw",
                                "space_type": "cosine",
                                "engine": "nmslib",
                                "parameters": {"ef_construction": 128, "m": 16},
                            },
                        },
                        "text": {"type": "text"},
                        "metadata": {"type": "object"},
                        "source_key": {"type": "keyword"},
                        "embedding_model": {"type": "keyword"},
                        "embedding_dimension": {"type": "integer"},
                        "page_number": {"type": "integer"},
                        "document_name": {"type": "keyword"},
                    }
                },
            }

            # Create the index
            opensearch_client.indices.create(index=OPENSEARCH_INDEX, body=index_body)
            logger.info(f"Created OpenSearch index: {OPENSEARCH_INDEX}")

            # Wait a moment for the index to be fully created
            time.sleep(2)

        return True

    except Exception as e:
        logger.error(f"Error creating OpenSearch index: {str(e)}")
        raise e


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
            "page_number": chunk_data.get("page_number", 0),
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
