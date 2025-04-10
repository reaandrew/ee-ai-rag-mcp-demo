import json
import logging
import os
import traceback
from src.utils import opensearch_utils, bedrock_utils

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Use the Lambda runtime's AWS_REGION environment variable
region = os.environ.get("AWS_REGION", "eu-west-2")

# Get environment variables
OPENSEARCH_DOMAIN = os.environ.get("OPENSEARCH_DOMAIN", "ee-ai-rag-mcp-demo-vectors")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", None)  # From Terraform
OPENSEARCH_INDEX = os.environ.get("OPENSEARCH_INDEX", "rag-vectors")
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL_ID = os.environ.get("LLM_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

# Additional flags for authentication
USE_IAM_AUTH = os.environ.get("USE_IAM_AUTH", "true").lower() == "true"
USE_AOSS = os.environ.get("USE_AOSS", "false").lower() == "true"

# Create the OpenSearch client
opensearch_client = opensearch_utils.get_opensearch_client()


def generate_embedding(text):
    """
    Generate embeddings for the provided text using AWS Bedrock Titan.

    Args:
        text (str): The text to generate embeddings for

    Returns:
        list: The embedding vector
    """
    return bedrock_utils.generate_embedding(text, model_id=EMBEDDING_MODEL_ID)


def search_opensearch(query_embedding, top_k=5):
    """
    Search OpenSearch for similar documents using vector search.

    Args:
        query_embedding (list): The embedding vector for the query
        top_k (int): Number of results to return

    Returns:
        list: List of search results with text and metadata
    """
    return opensearch_utils.search_opensearch(query_embedding, top_k=top_k)


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
        prompt = bedrock_utils.create_claude_prompt(query, formatted_results)

        # 6. Generate response from Claude
        response_text = bedrock_utils.generate_llm_response(prompt, model_id=LLM_MODEL_ID)

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
