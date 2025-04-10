import json
import boto3
import logging
import os
import traceback
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use the Lambda runtime's AWS_REGION environment variable
region = os.environ.get("AWS_REGION", "eu-west-2")

# Initialize AWS clients
bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)

# Get environment variables
OPENSEARCH_DOMAIN = os.environ.get("OPENSEARCH_DOMAIN", "ee-ai-rag-mcp-demo-vectors")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", None)  # From Terraform
OPENSEARCH_INDEX = os.environ.get("OPENSEARCH_INDEX", "rag-vectors")
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL_ID = os.environ.get("LLM_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

# Additional flags for authentication
USE_IAM_AUTH = os.environ.get("USE_IAM_AUTH", "true").lower() == "true"
USE_AOSS = os.environ.get("USE_AOSS", "false").lower() == "true"


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
        secret_name = "ee-ai-rag-mcp-demo/opensearch-master-credentials-v2"
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
    This separated to make testing easier, as AWS credentials may not be
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

        # First try to get credentials from Secrets Manager
        username, password = get_opensearch_credentials()

        # If we have username/password from Secrets Manager, use basic auth
        if username and password:
            logger.info(f"Using Secrets Manager credentials for user: {username}")
            try:
                # Try with username/password first
                client = OpenSearch(
                    hosts=[{"host": host, "port": 443}],
                    http_auth=(username, password),
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection,
                    timeout=30,
                )
                # Test the connection
                client.info()
                logger.info("Successfully connected to OpenSearch with username/password")
                return client
            except Exception as auth_err:
                logger.warning(f"Basic auth failed: {str(auth_err)}. Trying IAM authentication...")
                # Fall through to IAM authentication if basic auth fails

        # Use IAM authentication
        credentials = boto3.Session().get_credentials()
        if credentials:
            logger.info("Using IAM authentication for OpenSearch")

            # Try with "es" service name (older OpenSearch/Elasticsearch)
            try:
                awsauth = AWS4Auth(
                    credentials.access_key,
                    credentials.secret_key,
                    region,
                    "es",
                    session_token=credentials.token,
                )

                client = OpenSearch(
                    hosts=[{"host": host, "port": 443}],
                    http_auth=awsauth,
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection,
                    timeout=30,
                )
                # Test the connection
                client.info()
                logger.info(
                    "Successfully connected to OpenSearch with IAM authentication (es service)"
                )
                return client
            except Exception as es_err:
                logger.warning(
                    f"IAM auth with 'es' service failed: {str(es_err)}. Trying 'aoss' service..."
                )

            # Try with "aoss" service name (OpenSearch Serverless)
            try:
                awsauth = AWS4Auth(
                    credentials.access_key,
                    credentials.secret_key,
                    region,
                    "aoss",
                    session_token=credentials.token,
                )

                client = OpenSearch(
                    hosts=[{"host": host, "port": 443}],
                    http_auth=awsauth,
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection,
                    timeout=30,
                )
                # Test the connection
                client.info()
                logger.info(
                    "Successfully connected to OpenSearch with IAM authentication (aoss service)"
                )
                return client
            except Exception as aoss_err:
                logger.warning(f"IAM auth with 'aoss' service failed: {str(aoss_err)}")

            # As a last resort, try with "opensearch" service name
            try:
                awsauth = AWS4Auth(
                    credentials.access_key,
                    credentials.secret_key,
                    region,
                    "opensearch",
                    session_token=credentials.token,
                )

                client = OpenSearch(
                    hosts=[{"host": host, "port": 443}],
                    http_auth=awsauth,
                    use_ssl=True,
                    verify_certs=True,
                    connection_class=RequestsHttpConnection,
                    timeout=30,
                )
                # Test the connection
                client.info()
                logger.info(
                    "Successfully connected to OpenSearch with IAM auth (opensearch service)"
                )
                return client
            except Exception as opensearch_err:
                logger.error(
                    f"All authentication methods failed. Last error: {str(opensearch_err)}"
                )

            logger.error("All authentication methods failed for OpenSearch")

        else:
            logger.warning("No credentials available for OpenSearch authentication")

        # In test environments, we might want to return a mock client
        return None

    except Exception as e:
        logger.error(f"Error creating OpenSearch client: {str(e)}")
        # In a test environment, we might still want to continue
        return None


# Create the OpenSearch client
opensearch_client = get_opensearch_client()


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
        response = bedrock_runtime.invoke_model(modelId=EMBEDDING_MODEL_ID, body=request_body)

        # Parse response
        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding", [])

        logger.info(f"Successfully generated embedding with dimension {len(embedding)}")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise e


def search_opensearch(query_embedding, top_k=5):
    """
    Search OpenSearch for similar documents using vector search.

    Args:
        query_embedding (list): The embedding vector for the query
        top_k (int): Number of results to return

    Returns:
        list: List of search results with text and metadata
    """
    try:
        if not opensearch_client:
            raise ValueError("OpenSearch client not available")

        # Perform kNN search against the embedding field
        search_body = {
            "size": top_k,
            "query": {"knn": {"embedding": {"vector": query_embedding, "k": top_k}}},
            "_source": ["text", "document_name", "page_number", "metadata"],
        }

        # Execute the search
        response = opensearch_client.search(index=OPENSEARCH_INDEX, body=search_body)

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


def format_results_for_prompt(search_results):
    """
    Format search results into a string for inclusion in the LLM prompt.

    Args:
        search_results (list): List of search results with text and metadata

    Returns:
        str: Formatted string of search results
    """
    formatted_text = ""

    for i, result in enumerate(search_results, 1):
        doc_name = result.get("document_name", "Unknown Document")
        page_num = result.get("page_number", 0)
        text = result.get("text", "").strip()

        formatted_text += f"[Document {i}: {doc_name}, Page {page_num}]\n{text}\n\n"

    return formatted_text


def create_claude_prompt(query, formatted_results):
    """
    Create a prompt for Claude to answer the query based on search results.

    Args:
        query (str): The user's query
        formatted_results (str): Formatted search results

    Returns:
        dict: The formatted prompt for Claude
    """
    system_prompt = """You are a policy assistant that helps users find policy information.
Your job is to provide accurate answers based ONLY on the policy information provided.
If the information isn't in the excerpts, politely say you don't have it.
Always cite document names and page numbers when providing information.
Be concise but comprehensive in your answers."""

    human_message = f"""I have a question about company policies: {query}

Here are the most relevant policy excerpts:

{formatted_results}

Based on these excerpts only, please answer with document and page citations."""

    # Format prompt for Claude 3
    prompt = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": human_message}],
    }

    return prompt


def generate_llm_response(prompt):
    """
    Generate a response from Claude based on the prompt.

    Args:
        prompt (dict): The formatted prompt for Claude

    Returns:
        str: The generated response
    """
    try:
        # Call Bedrock to generate response
        response = bedrock_runtime.invoke_model(modelId=LLM_MODEL_ID, body=json.dumps(prompt))

        # Parse response
        response_body = json.loads(response["body"].read())

        # Extract the assistant's message
        if "content" in response_body:
            # For Anthropic Message API format
            return response_body["content"][0]["text"]
        elif "completion" in response_body:
            # For older Anthropic Complete API format
            return response_body["completion"]
        else:
            logger.error(f"Unexpected response format: {response_body}")
            return "I'm sorry, I couldn't generate a response at this time."

    except Exception as e:
        logger.error(f"Error generating LLM response: {str(e)}")
        logger.error(traceback.format_exc())
        raise e


def extract_query_from_event(event):
    """
    Extract the query from the API Gateway event.

    Args:
        event (dict): The API Gateway event

    Returns:
        str: The extracted query
    """
    try:
        # Check if the event has a body
        if "body" in event:
            # Parse the body as JSON
            body = json.loads(event.get("body", "{}"))
            query = body.get("query", "")

            if not query:
                logger.warning("No query found in request body")
                raise ValueError("No query parameter found in request")

            return query
        else:
            logger.warning("No body found in event")
            raise ValueError("Invalid request format")

    except json.JSONDecodeError:
        logger.error("Failed to parse request body as JSON")
        raise ValueError("Invalid JSON in request body")
    except Exception as e:
        logger.error(f"Error extracting query from event: {str(e)}")
        raise e


def extract_sources(search_results):
    """
    Extract source information from search results for the response.

    Args:
        search_results (list): List of search results

    Returns:
        list: List of source information dictionaries
    """
    sources = []

    for result in search_results:
        source = {
            "document_name": result.get("document_name", "Unknown Document"),
            "page_number": result.get("page_number", 0),
        }

        # Only add if not already in sources list
        if source not in sources:
            sources.append(source)

    return sources


def lambda_handler(event, context):
    """
    Lambda function handler that processes natural language policy queries.

    Args:
        event (dict): Event data from API Gateway
        context (LambdaContext): Lambda context

    Returns:
        dict: Response with query results
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # 1. Extract the query from the event
        query = extract_query_from_event(event)
        logger.info(f"Processing query: {query}")

        # 2. Generate embedding for the query
        query_embedding = generate_embedding(query)

        # 3. Search OpenSearch with the query embedding
        search_results = search_opensearch(query_embedding, top_k=5)

        # 4. Format search results for LLM context
        formatted_results = format_results_for_prompt(search_results)

        # 5. Create prompt for Claude
        prompt = create_claude_prompt(query, formatted_results)

        # 6. Generate response from Claude
        response_text = generate_llm_response(prompt)

        # 7. Extract source information for the response
        sources = extract_sources(search_results)

        # 8. Return formatted response
        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # For CORS
            },
            "body": json.dumps({"query": query, "answer": response_text, "sources": sources}),
        }

    except ValueError as ve:
        # Handle validation errors
        logger.error(f"Validation error: {str(ve)}")
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": str(ve)}),
        }
    except Exception as e:
        # Handle other errors
        logger.error(f"Error processing query: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "headers": {"Content-Type": "application/json", "Access-Control-Allow-Origin": "*"},
            "body": json.dumps({"error": "An error occurred while processing your query"}),
        }
