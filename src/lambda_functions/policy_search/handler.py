import json
import logging
import os
import traceback

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
            logging.error("Could not import utils modules from standard locations")
            raise

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Use the Lambda runtime's AWS_REGION environment variable
region = os.environ.get("AWS_REGION", "eu-west-2")

# Get environment variables
OPENSEARCH_DOMAIN = os.environ.get("OPENSEARCH_DOMAIN", "ee-ai-rag-mcp-demo-vectors")
OPENSEARCH_ENDPOINT = os.environ.get("OPENSEARCH_ENDPOINT", None)
OPENSEARCH_INDEX = os.environ.get("OPENSEARCH_INDEX", "rag-vectors")
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL_ID = os.environ.get("LLM_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")

USE_IAM_AUTH = os.environ.get("USE_IAM_AUTH", "true").lower() == "true"
USE_AOSS = os.environ.get("USE_AOSS", "false").lower() == "true"

# Create the OpenSearch client
opensearch_client = opensearch_utils.get_opensearch_client()


def generate_embedding(text):
    """
    Generate embeddings for the provided text using AWS Bedrock Titan.
    """
    return bedrock_utils.generate_embedding(text, model_id=EMBEDDING_MODEL_ID)


def search_opensearch(query_embedding, top_k=5):
    """
    Search OpenSearch for similar documents using vector search.
    """
    return opensearch_utils.search_opensearch(query_embedding, top_k=top_k)


def format_results_for_prompt(search_results):
    """
    Format search results into a string for inclusion in the LLM prompt.
    Instead of numbering the documents sequentially, this version uses the actual
    document name and presents the page range.
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
    """
    try:
        if "body" in event:
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
    """
    sources = []
    for result in search_results:
        source = {
            "document_name": result.get("document_name", "Unknown Document"),
            "page_number": result.get("page_number", 0),
        }
        if source not in sources:
            sources.append(source)
    return sources


def lambda_handler(event, context):
    """
    Lambda function handler that processes natural language policy queries.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        # Handle OPTIONS method for CORS preflight requests
        if event.get("httpMethod") == "OPTIONS":
            return {
                "statusCode": 200,
                "headers": {
                    "Content-Type": "application/json",
                    "Access-Control-Allow-Origin": "*",
                    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                    "Access-Control-Allow-Headers": (
                        "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
                    ),
                },
                "body": json.dumps({"message": "CORS preflight request successful"}),
            }

        if hasattr(context, "function_name"):
            logger.info(
                f"Lambda context: {context.function_name}, "
                f"{context.function_version}, {context.aws_request_id}"
            )

        logger.info(
            f"Environment variables: OPENSEARCH_ENDPOINT={OPENSEARCH_ENDPOINT}, "
            f"USE_IAM_AUTH={USE_IAM_AUTH}, OPENSEARCH_INDEX={OPENSEARCH_INDEX}"
        )

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

        return {
            "statusCode": 200,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",  # For CORS
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
                ),
            },
            "body": json.dumps({"query": query, "answer": response_text, "sources": sources}),
        }

    except ValueError as ve:
        logger.error(f"Validation error: {str(ve)}")
        return {
            "statusCode": 400,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
                ),
            },
            "body": json.dumps({"error": str(ve)}),
        }
    except Exception as e:
        logger.error(f"Error processing query: {str(e)}")
        logger.error(traceback.format_exc())
        return {
            "statusCode": 500,
            "headers": {
                "Content-Type": "application/json",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
                "Access-Control-Allow-Headers": (
                    "Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token"
                ),
            },
            "body": json.dumps({"error": "An error occurred while processing your query"}),
        }
