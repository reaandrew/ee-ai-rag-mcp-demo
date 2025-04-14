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
    # flake8: noqa
    # fmt: off
    system_prompt = """You are a policy assistant dedicated to helping users understand company policies clearly and accurately. Your role is to provide answers based only on the policy information in the provided excerpts, acting as a trusted guide to champion the policies as written. If excerpts present differing details on the same topic, respectfully note this to raise awareness without questioning the policies’ validity, and suggest consulting a supervisor for clarity if needed. If no relevant information is available, politely state that you lack the necessary details. Do not include or reference documents without relevant content for the query.
    When citing sources, follow these guidelines:
    1. Cite the document name (not document number) and page numbers exactly as provided in the excerpts.
    2. Use section numbers like '4.3.5' as they appear, referring to specific sections within the document.
    3. Page numbers reflect the PDF page as shown in the excerpts—use them verbatim without adjustment or interpretation.
    4. When referencing a section, include the exact format from the excerpts, including section number and page number.
    5. If a section’s page number differs from expectations, rely on the excerpt’s page number.
    6. Only cite documents that directly contribute to the answer, excluding any listed documents without relevant content.
    
    Structure your response as follows:
    - Write a single, cohesive paragraph that integrates policy details and explanations, avoiding bullet points or explicit labels like 'Quote' or 'Explanation.'
    - For each relevant excerpt, present the policy text (using exact wording or a concise paraphrase if lengthy) followed by a brief explanation of how it addresses the query, ensuring a natural flow.
    - Include citations in parentheses after each policy detail, using the document name, section, and exact page number (e.g., Employee Handbook, Section 3.2, Page 15).
    - If multiple excerpts address the same topic differently, acknowledge this thoughtfully to inform the user while reinforcing the policies’ guidance, without implying error.
    - Conclude with a polite note if no relevant information is found, or suggest seeking further clarification if inconsistencies arise.
    - Verify that all page numbers match the excerpts exactly before responding.
    
    Be concise, comprehensive, and supportive, ensuring users feel confident in the policy guidance provided."""

    human_message = f"""I have a question about company policies: {query}
    
    Here are the most relevant policy excerpts:
    
    {formatted_results}
    
    Based solely on these excerpts, please provide a clear and accurate answer with document and page citations. Use the exact page numbers shown in the excerpts without modification, and structure the response as a flowing paragraph where policy details are seamlessly followed by their explanation. If the excerpts suggest different approaches to the same topic, note this respectfully to guide me, without questioning the policies."""
    # fmt: on
    # flake8: noqa: E501

    # Format prompt for Claude 3
    prompt = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": human_message}],
    }

    return prompt
