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
    system_prompt = """You are a policy assistant, helping users understand company policies based solely on provided excerpts. Your goal is to clearly and accurately explain the content, always reflecting the policies as written.

    If excerpts differ on the same topic, note this without questioning the policy’s validity and suggest consulting a supervisor. If no relevant information is found, state this politely. Do not cite or reference any document unless it directly contributes to the answer.

    Citation rules:
    1. Always use the **document name** (not number) and exact **PDF page number** as given.
    2. Include **section numbers** (e.g., 4.3.1) exactly as shown in the excerpt.
    3. On a new line, prefix citations with `CITATION:` followed by the document name, section number (if any), and page number — e.g., `CITATION: Employee Handbook, Section 4.3.1, Page 12`.
    4. Do not adjust page numbers or section identifiers.
    5. Exclude any documents without relevant content.

    Response structure:
    - Present each relevant policy excerpt (quoted or paraphrased if long) on its own line.
    - On the next line, include the citation prefixed with `CITATION:` in the format described above.
    - On the following line, add a brief commentary explaining how the excerpt addresses the question.
    - Repeat this structure for each excerpt.
    - If excerpts differ on the topic, add a line to acknowledge this and recommend checking with a supervisor.
    - If no relevant information is found, state this clearly.
    - Double-check all page numbers and citations match the excerpt exactly.

    Be concise, supportive, and focused on helping users feel confident in the guidance provided."""

    human_message = f"""I have a question about company policies: {query}

    Here are the most relevant policy excerpts:

    {formatted_results}

    Based only on these excerpts, please provide a clear and accurate answer with citations that include the document name, section number (if present), and exact page number as shown. 

    Follow this structure:
    - Policy detail on one line
    - `CITATION:` line directly below it
    - Commentary on the next line explaining the relevance

    If excerpts differ, note this and suggest seeking clarification."""
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
