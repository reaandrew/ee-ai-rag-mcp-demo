"""
OpenSearch utilities for connecting to and searching OpenSearch.
Shared between Lambda functions to reduce code duplication.
"""
import os
import json
import boto3
import logging
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Set up logging
logger = logging.getLogger(__name__)

# Region is set from the Lambda environment
region = os.environ.get("AWS_REGION", "eu-west-2")

# Get common environment variables
OPENSEARCH_DOMAIN = os.environ.get("OPENSEARCH_DOMAIN", "ee-ai-rag-mcp-demo-vectors")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", None)  # From Terraform
OPENSEARCH_INDEX = os.environ.get("OPENSEARCH_INDEX", "rag-vectors")
USE_IAM_AUTH = os.environ.get("USE_IAM_AUTH", "true").lower() == "true"
USE_AOSS = os.environ.get("USE_AOSS", "false").lower() == "true"


def get_opensearch_credentials():
    """
    Retrieve OpenSearch credentials from AWS Secrets Manager.
    Returns a tuple of (username, password) or (None, None) if not found.
    """
    try:
        # Create a Secrets Manager client
        secrets_client = boto3.client("secretsmanager", region_name=region)

        # Get the secret value
        secret_name = "ee-ai-rag-mcp-demo/opensearch-master-credentials-v2"
        response = secrets_client.get_secret_value(SecretId=secret_name)

        # Parse the secret JSON string
        secret = json.loads(response["SecretString"])
        return secret.get("username"), secret.get("password")

    except Exception as e:
        logger.warning(f"Could not retrieve OpenSearch credentials from Secrets Manager: {str(e)}")
        logger.warning("Will attempt to use IAM authentication instead")
        return None, None


def get_opensearch_client():
    """
    Create and return an OpenSearch client with IAM authentication.
    This is separated to make testing easier, as AWS credentials may not be
    available in test environments.
    """
    try:
        # Determine the host endpoint
        if OPENSEARCH_ENDPOINT:
            host = OPENSEARCH_ENDPOINT
            logger.info(f"Using OpenSearch endpoint from environment: {host}")
        else:
            host = f"{OPENSEARCH_DOMAIN}.{region}.es.amazonaws.com"
            logger.info(f"Using constructed OpenSearch endpoint: {host}")

        # Use IAM authentication (FGAC is disabled, so this is the most direct method)
        credentials = boto3.Session().get_credentials()
        if credentials:
            logger.info("Using IAM authentication for OpenSearch")
            # Create AWS4Auth object for the 'es' service
            awsauth = AWS4Auth(
                credentials.access_key,
                credentials.secret_key,
                region,
                "es",
                session_token=credentials.token,
            )

            # Create OpenSearch client with IAM auth
            client = OpenSearch(
                hosts=[{"host": host, "port": 443}],
                http_auth=awsauth,
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30,
            )
            # Test the connection
            try:
                client.info()
                logger.info("Successfully connected to OpenSearch with IAM auth")
                return client
            except Exception as e:
                logger.error(f"OpenSearch connection failed: {str(e)}")
                # Log more detailed error information
                if "403" in str(e):
                    logger.error("Access denied (403). Check IAM role permissions.")
                elif "404" in str(e):
                    logger.error("Endpoint not found (404). Check domain name.")
                else:
                    logger.error(f"Connection error details: {type(e).__name__}")
        else:
            logger.warning("No credentials available for OpenSearch authentication")

        # In test environments, we might want to return a mock client
        return None

    except Exception as e:
        logger.error(f"Error creating OpenSearch client: {str(e)}")
        # In a test environment, we might still want to continue
        return None


def search_opensearch(query_embedding, top_k=5):
    """
    Search OpenSearch for similar documents using vector search.

    Args:
        query_embedding (list): The embedding vector for the query
        top_k (int): Number of results to return

    Returns:
        list: List of search results with text and metadata
    """
    client = get_opensearch_client()

    try:
        if not client:
            raise ValueError("OpenSearch client not available")

        # Perform kNN search against the embedding field
        search_body = {
            "size": top_k,
            "query": {"knn": {"embedding": {"vector": query_embedding, "k": top_k}}},
            "_source": ["text", "document_name", "page_number", "metadata"],
        }

        # Execute the search
        response = client.search(index=OPENSEARCH_INDEX, body=search_body)

        # Extract search results
        hits = response.get("hits", {}).get("hits", [])
        results = []

        for hit in hits:
            source = hit.get("_source", {})
            results.append(
                {
                    "text": source.get("text", ""),
                    "document_name": source.get("document_name", "Unknown Document"),
                    "page_number": source.get("page_number", 0),
                    "metadata": source.get("metadata", {}),
                    "score": hit.get("_score", 0),
                }
            )

        logger.info(f"Found {len(results)} search results for the query")
        return results

    except Exception as e:
        logger.error(f"Error searching OpenSearch: {str(e)}")
        raise e


def get_index_body():
    """
    Get the OpenSearch index configuration with correct mappings for vector search.
    Extracted to separate function to reduce cognitive complexity.
    Returns:
        dict: The index configuration body
    """
    return {
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
                    "dimension": 1024,  # Dimension for Titan embeddings
                    "method": {
                        "name": "hnsw",
                        "space_type": "cosinesimil",  # Correct value for cosine similarity
                        "engine": "nmslib",
                        "parameters": {"ef_construction": 128, "m": 16},
                    },
                },
                "text": {"type": "text"},
                "metadata": {"type": "object"},
                "source_key": {"type": "keyword"},
                "embedding_model": {"type": "keyword"},
                "embedding_dimension": {"type": "integer"},
                # Use keyword type for page_number to support formats like "1-2"
                "page_number": {"type": "keyword"},
                "document_name": {"type": "keyword"},
            }
        },
    }


def handle_auth_error():
    """
    Handle authorization errors with detailed logging.
    Extracted to separate function to reduce cognitive complexity.
    """
    logger.error("Authorization failure. Check IAM permissions and OpenSearch policy.")
    logger.error(f"Using endpoint: {OPENSEARCH_ENDPOINT}")
    try:
        # Try to get IAM role info for debugging
        sts_client = boto3.client("sts")
        identity = sts_client.get_caller_identity()
        logger.error(f"Lambda execution identity: {identity.get('Arn')}")
    except Exception as sts_error:
        logger.error(f"Could not get caller identity: {str(sts_error)}")


def create_index_if_not_exists(client, index_name=None):
    """
    Create OpenSearch index with embedding mapping if it doesn't exist.
    The index is configured with the appropriate mapping for vector search.

    Args:
        client: OpenSearch client
        index_name: Name of the index to create (defaults to OPENSEARCH_INDEX)

    Returns:
        bool: True if index exists or was created successfully, False if client is unavailable
        or the operation failed
    """
    if index_name is None:
        index_name = OPENSEARCH_INDEX

    # Check if OpenSearch client is available
    if not client:
        logger.warning("OpenSearch client not available, skipping index creation")
        return False

    try:
        # Check if index already exists
        if client.indices.exists(index=index_name):
            logger.info(f"Index {index_name} already exists")
            return True

        # Index doesn't exist, create it
        logger.info(f"Creating OpenSearch index: {index_name}")
        # Get the index configuration
        index_body = get_index_body()
        # Create the index
        client.indices.create(index=index_name, body=index_body)
        logger.info(f"Created OpenSearch index: {index_name}")
        return True
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error creating OpenSearch index: {error_message}")
        # Handle specific error types
        if "resource_already_exists_exception" in error_message:
            logger.info(f"Index {index_name} already exists, continuing without error.")
            return True
        if "403" in error_message or "AuthorizationException" in error_message:
            handle_auth_error()
        # For all other errors
        return False
