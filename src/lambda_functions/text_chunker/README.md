# Text Chunker Lambda Function

This Lambda function processes text files from the extracted-text S3 bucket, chunks the text content, and stores the chunks in a chunked-text S3 bucket for use in RAG applications.

## Features

- Listens to S3 ObjectCreated events from the extracted-text bucket
- Uses RecursiveCharacterTextSplitter from LangChain to create optimized text chunks
- Preserves metadata from source documents
- Creates individual JSON files for each chunk
- Generates a manifest file with information about all chunks
- Configurable chunk size and overlap via environment variables

## Configuration

The function can be configured using the following environment variables:

- `CHUNKED_TEXT_BUCKET`: The S3 bucket where chunks will be stored (default: "ee-ai-rag-mcp-demo-chunked-text")
- `CHUNKED_TEXT_PREFIX`: Prefix for chunk objects (default: "ee-ai-rag-mcp-demo")
- `CHUNK_SIZE`: Maximum size of each chunk in characters (default: 1000)
- `CHUNK_OVERLAP`: Number of characters of overlap between chunks (default: 200)

## Input

Input text files must be in .txt format and stored in the extracted-text S3 bucket.

## Output

For each input text file, the function creates:
- Multiple JSON files containing individual chunks with relevant metadata
- A manifest file with information about all chunks

## Local Testing

```bash
python -m unittest tests/lambda_functions/text_chunker/test_handler.py
```