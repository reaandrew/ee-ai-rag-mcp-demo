# Vector Generator Lambda Function

This Lambda function subscribes to S3 events from the chunked_text bucket. It processes each JSON chunk file, extracts the text content, and generates vector embeddings using AWS Bedrock Titan embedding model. The resulting vectors are stored in a dedicated S3 bucket for later use in RAG applications.

## Features

- Subscribes to S3 creation events from the chunked_text bucket
- Processes JSON chunks containing text segments
- Generates vector embeddings using AWS Bedrock Titan models
- Preserves all original chunk metadata and adds embedding information
- Saves the resulting vectors to a dedicated S3 bucket

## Configuration

The function can be configured using the following environment variables:

- `CHUNKED_TEXT_BUCKET`: Name of the S3 bucket containing chunked text (default: "ee-ai-rag-mcp-demo-chunked-text")
- `VECTOR_BUCKET`: Name of the S3 bucket for storing vectors (default: "ee-ai-rag-mcp-demo-vectors")
- `VECTOR_PREFIX`: Prefix for objects in the vector bucket (default: "ee-ai-rag-mcp-demo")
- `MODEL_ID`: AWS Bedrock model ID for generating embeddings (default: "amazon.titan-embed-text-v1")