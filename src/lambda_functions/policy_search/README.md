# Policy Search Lambda Function

This Lambda function provides a natural language query interface for company policies. It integrates with API Gateway, Bedrock, and OpenSearch to create a RAG (Retrieval-Augmented Generation) system.

## Flow

1. User submits a query through API Gateway
2. Lambda extracts the query and generates embeddings using Bedrock Titan
3. Lambda searches OpenSearch for relevant policy chunks
4. The top results are formatted and sent to Bedrock Claude 3 Sonnet
5. Claude provides a response based on the policy information
6. Response is returned to the user with source information

## API Request Format

```json
{
  "query": "What is our password policy?"
}
```

## API Response Format

```json
{
  "query": "What is our password policy?",
  "answer": "Based on the policy excerpts provided, passwords must be changed every 90 days and meet the following requirements: at least 12 characters in length, contain uppercase and lowercase letters, numbers, and special characters. (Acceptable Encryption Policy, Page 3)",
  "sources": [
    {
      "document_name": "Acceptable Encryption Policy",
      "page_number": 3
    }
  ]
}
```

## Environment Variables

- `OPENSEARCH_DOMAIN`: The OpenSearch domain name
- `OPENSEARCH_ENDPOINT`: The OpenSearch endpoint URL
- `OPENSEARCH_INDEX`: The OpenSearch index name
- `EMBEDDING_MODEL_ID`: The Bedrock model ID for embeddings (Titan)
- `LLM_MODEL_ID`: The Bedrock model ID for text generation (Claude)
- `USE_IAM_AUTH`: Whether to use IAM authentication for OpenSearch
- `USE_AOSS`: Whether to use OpenSearch Serverless

## Permissions

The Lambda function requires:
- Bedrock access to invoke models
- OpenSearch permissions for searching
- Secrets Manager access for OpenSearch credentials
- CloudWatch Logs access for logging