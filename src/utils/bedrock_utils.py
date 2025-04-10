"""
AWS Bedrock utilities for generating embeddings and LLM responses.
Shared between Lambda functions to reduce code duplication.
"""
import os
import json
import boto3
import logging
import traceback

# Set up logging
logger = logging.getLogger(__name__)

# Region is set from the Lambda environment
region = os.environ.get("AWS_REGION", "eu-west-2")

# Initialize AWS clients
bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)

# Get common environment variables
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL_ID = os.environ.get("LLM_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")


def generate_embedding(text, model_id=None):
    """
    Generate embeddings for the provided text using AWS Bedrock.

    Args:
        text (str): The text to generate embeddings for
        model_id (str, optional): Model ID to use, defaults to EMBEDDING_MODEL_ID

    Returns:
        list: The embedding vector
    """
    try:
        # Use the default model if none is specified
        if model_id is None:
            model_id = EMBEDDING_MODEL_ID
        # Prepare request body for Titan embedding model
        request_body = json.dumps({"inputText": text})

        # Call Bedrock to generate embeddings
        response = bedrock_runtime.invoke_model(modelId=model_id, body=request_body)

        # Parse response
        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding", [])

        logger.info(f"Successfully generated embedding with dimension {len(embedding)}")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise e


def generate_llm_response(prompt, model_id=None):
    """
    Generate a response from Claude based on the prompt.

    Args:
        prompt (dict): The formatted prompt for Claude
        model_id (str, optional): Model ID to use, defaults to LLM_MODEL_ID

    Returns:
        str: The generated response
    """
    try:
        # Use the default model if none is specified
        if model_id is None:
            model_id = LLM_MODEL_ID
        # Call Bedrock to generate response
        response = bedrock_runtime.invoke_model(modelId=model_id, body=json.dumps(prompt))

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
