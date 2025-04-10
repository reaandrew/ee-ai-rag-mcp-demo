"""
Full example of AWS Bedrock utilities + tests, using unittest.mock.patch.
Just run:  pytest test_bedrock_utils.py
"""
import os
import json
import logging
import traceback

import pytest
from unittest.mock import patch, MagicMock
import boto3

# ---------------------------------------------------------------------------
# This is our "bedrock_utils" module code
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# Default region
region = os.environ.get("AWS_REGION", "eu-west-2")

# "Global" Bedrock client
bedrock_runtime = boto3.client("bedrock-runtime", region_name=region)

# Model IDs
EMBEDDING_MODEL_ID = os.environ.get("EMBEDDING_MODEL_ID", "amazon.titan-embed-text-v2:0")
LLM_MODEL_ID = os.environ.get("LLM_MODEL_ID", "anthropic.claude-3-sonnet-20240229-v1:0")


def generate_embedding(text, model_id=None):
    """
    Generate embeddings for the provided text using AWS Bedrock.
    """
    try:
        if model_id is None:
            model_id = EMBEDDING_MODEL_ID

        request_body = json.dumps({"inputText": text})
        response = bedrock_runtime.invoke_model(modelId=model_id, body=request_body)

        response_body = json.loads(response["body"].read())
        embedding = response_body.get("embedding", [])
        logger.info(f"Successfully generated embedding: dimension {len(embedding)}")
        return embedding
    except Exception as e:
        logger.error(f"Error generating embedding: {str(e)}")
        raise


def generate_llm_response(prompt, model_id=None):
    """
    Generate a response from Claude based on the prompt.
    """
    try:
        if model_id is None:
            model_id = LLM_MODEL_ID

        response = bedrock_runtime.invoke_model(modelId=model_id, body=json.dumps(prompt))
        response_body = json.loads(response["body"].read())

        # Anthropic's newer "Message" format
        if "content" in response_body and response_body["content"]:
            return response_body["content"][0]["text"]

        # Anthropic's older "Complete API" format
        elif "completion" in response_body:
            return response_body["completion"]

        else:
            logger.error(f"Unexpected response format: {response_body}")
            return "I'm sorry, I couldn't generate a response at this time."

    except Exception as e:
        logger.error(f"Error generating LLM response: {str(e)}")
        logger.error(traceback.format_exc())
        raise


def create_claude_prompt(query, formatted_results):
    """
    Create a prompt for Claude to answer the query based on search results.
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

    return {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1000,
        "system": system_prompt,
        "messages": [{"role": "user", "content": human_message}],
    }


# ---------------------------------------------------------------------------
# Below are the tests:
# ---------------------------------------------------------------------------


@pytest.fixture
def mock_bedrock_response():
    """Mock embedding response with [0.1, 0.2, 0.3]."""
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps({"embedding": [0.1, 0.2, 0.3]})
    return {"body": mock_body, "ResponseMetadata": {"HTTPStatusCode": 200}}


@pytest.fixture
def mock_bedrock_llm_response_message_api():
    """Mock LLM response using the Anthropic 'Message' API style."""
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(
        {
            "content": [{"text": "This is a test response from Claude"}],
            "id": "msg_01AB23CD",
            "model": "anthropic.claude-3-sonnet-20240229-v1:0",
            "role": "assistant",
            "type": "message",
        }
    )
    return {"body": mock_body, "ResponseMetadata": {"HTTPStatusCode": 200}}


@pytest.fixture
def mock_bedrock_llm_response_complete_api():
    """Mock LLM response using the older 'Complete' API style."""
    mock_body = MagicMock()
    mock_body.read.return_value = json.dumps(
        {
            "completion": "This is a test response from Claude using Complete API",
            "model": "anthropic.claude-3-sonnet-20240229-v1:0",
        }
    )
    return {"body": mock_body, "ResponseMetadata": {"HTTPStatusCode": 200}}


class TestGenerateEmbedding:
    @patch(__name__ + ".bedrock_runtime")
    def test_successful_embedding_generation(self, mock_bedrock, mock_bedrock_response):
        """Test that we get [0.1, 0.2, 0.3]."""
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        emb = generate_embedding("Test text")
        assert emb == [0.1, 0.2, 0.3]
        mock_bedrock.invoke_model.assert_called_once()

    @patch(__name__ + ".bedrock_runtime")
    def test_custom_model_id(self, mock_bedrock, mock_bedrock_response):
        """Test using a custom model ID."""
        mock_bedrock.invoke_model.return_value = mock_bedrock_response
        emb = generate_embedding("Test text", model_id="custom.embedding-model")
        assert emb == [0.1, 0.2, 0.3]
        # Check modelId used
        call_args = mock_bedrock.invoke_model.call_args[1]
        assert call_args["modelId"] == "custom.embedding-model"

    @patch(__name__ + ".bedrock_runtime")
    def test_error_handling(self, mock_bedrock):
        """Ensure we raise an exception if bedrock fails."""
        mock_bedrock.invoke_model.side_effect = Exception("Test error")
        with pytest.raises(Exception) as exc:
            generate_embedding("Text to embed")
        assert "Test error" in str(exc.value)


class TestGenerateLLMResponse:
    @patch(__name__ + ".bedrock_runtime")
    def test_message_api_response(self, mock_bedrock, mock_bedrock_llm_response_message_api):
        mock_bedrock.invoke_model.return_value = mock_bedrock_llm_response_message_api
        prompt = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 1000,
            "system": "You are a helpful assistant",
            "messages": [{"role": "user", "content": "Hello, how are you?"}],
        }
        response = generate_llm_response(prompt)
        assert response == "This is a test response from Claude"

    @patch(__name__ + ".bedrock_runtime")
    def test_complete_api_response(self, mock_bedrock, mock_bedrock_llm_response_complete_api):
        mock_bedrock.invoke_model.return_value = mock_bedrock_llm_response_complete_api
        prompt = {"prompt": "\n\nHuman: Hello\n\nAssistant:", "max_tokens_to_sample": 1000}
        response = generate_llm_response(prompt)
        assert response == "This is a test response from Claude using Complete API"

    @patch(__name__ + ".bedrock_runtime")
    def test_custom_model_id(self, mock_bedrock, mock_bedrock_llm_response_message_api):
        mock_bedrock.invoke_model.return_value = mock_bedrock_llm_response_message_api
        custom_model = "anthropic.claude-instant-v1"
        generate_llm_response({"messages": []}, model_id=custom_model)
        call_args = mock_bedrock.invoke_model.call_args[1]
        assert call_args["modelId"] == custom_model

    @patch(__name__ + ".bedrock_runtime")
    def test_unexpected_response_format(self, mock_bedrock):
        # Return something that doesn't have content or completion
        mock_body = MagicMock()
        mock_body.read.return_value = json.dumps({"unexpected_key": "value"})
        mock_bedrock.invoke_model.return_value = {"body": mock_body}
        resp = generate_llm_response({"messages": []})
        assert resp == "I'm sorry, I couldn't generate a response at this time."

    @patch(__name__ + ".bedrock_runtime")
    def test_error_handling(self, mock_bedrock):
        mock_bedrock.invoke_model.side_effect = Exception("LLM error")
        with pytest.raises(Exception) as exc:
            generate_llm_response({"messages": []})
        assert "LLM error" in str(exc.value)


class TestCreateClaudePrompt:
    def test_create_claude_prompt_format(self):
        query = "What is the vacation policy?"
        results = "Employee Handbook p.45: 20 days PTO per year."
        prompt = create_claude_prompt(query, results)

        assert "anthropic_version" in prompt
        assert prompt["anthropic_version"] == "bedrock-2023-05-31"
        assert "max_tokens" in prompt
        assert "system" in prompt
        assert "messages" in prompt
        assert len(prompt["messages"]) == 1
        assert prompt["messages"][0]["role"] == "user"

        # Check content
        user_text = prompt["messages"][0]["content"]
        assert "vacation policy?" in user_text
        assert "Employee Handbook p.45" in user_text


def test_bedrock_utils_exists():
    assert generate_embedding
    assert generate_llm_response
    assert create_claude_prompt
