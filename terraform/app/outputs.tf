output "raw_pdfs_bucket_name" {
  value       = aws_s3_bucket.raw_pdfs.bucket
  description = "The name of the S3 bucket for raw PDFs"
}

output "raw_pdfs_bucket_arn" {
  value       = aws_s3_bucket.raw_pdfs.arn
  description = "The ARN of the S3 bucket for raw PDFs"
}

output "logs_bucket_name" {
  value       = aws_s3_bucket.logs_bucket.bucket
  description = "The name of the S3 bucket for access logs"
}

output "logs_bucket_arn" {
  value       = aws_s3_bucket.logs_bucket.arn
  description = "The ARN of the S3 bucket for access logs"
}

output "deployed_version" {
  value       = var.app_version
  description = "The version of the application that was deployed"
}

output "extracted_text_bucket_name" {
  value       = aws_s3_bucket.extracted_text.bucket
  description = "The name of the S3 bucket for extracted text"
}

output "chunked_text_bucket_name" {
  value       = aws_s3_bucket.chunked_text.bucket
  description = "The name of the S3 bucket for chunked text"
}

output "vector_bucket_name" {
  value       = aws_s3_bucket.vectors.bucket
  description = "The name of the S3 bucket for vector embeddings"
}

output "vector_bucket_arn" {
  value       = aws_s3_bucket.vectors.arn
  description = "The ARN of the S3 bucket for vector embeddings"
}

output "vector_generator_lambda_name" {
  value       = aws_lambda_function.vector_generator.function_name
  description = "The name of the vector generator Lambda function"
}

output "opensearch_domain_endpoint" {
  value       = aws_opensearch_domain.vectors.endpoint
  description = "The endpoint of the OpenSearch domain for vector embeddings"
}

output "opensearch_dashboard_endpoint" {
  value       = aws_opensearch_domain.vectors.dashboard_endpoint
  description = "The dashboard endpoint of the OpenSearch domain for vector embeddings"
}

# Script content for API curl command
resource "local_file" "api_curl_script" {
  filename = "${path.module}/../../build/query_api.sh"
  content  = <<-EOT
#!/bin/bash

# API Query Script for RAG Policy Search System
# Generated by Terraform

API_URL="${aws_apigatewayv2_stage.policy_search_stage.invoke_url}/search"
AUTH_TOKEN="YOUR_AUTH_TOKEN"  # Replace with actual token (any value works with current implementation)

# Function to make API call
query_api() {
  local query="$1"
  
  # Create temporary file for request body
  TMPFILE=$(mktemp)
  echo "{\"query\": \"$query\"}" > $TMPFILE
  
  # Make the API call
  curl -X POST \\
    -H "Content-Type: application/json" \\
    -H "Authorization: Bearer $AUTH_TOKEN" \\
    --data @$TMPFILE \\
    "$API_URL"
    
  # Clean up temp file
  rm $TMPFILE
}

# Check if query was provided as argument
if [ $# -eq 0 ]; then
  echo "Usage: $0 \"your policy question here\""
  echo "Example: $0 \"What is our password policy?\""
  exit 1
fi

# Execute query
query_api "$1"
EOT

  # Make the script executable
  provisioner "local-exec" {
    command = "chmod +x ${path.module}/../../build/query_api.sh"
  }
}

# Output path to the generated script
output "api_curl_script_path" {
  value       = local_file.api_curl_script.filename
  description = "Path to the generated API curl script"
}

# Ensure Bruno directories exist
resource "null_resource" "ensure_bruno_dirs" {
  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/../../build/bruno/RAG-Policy-Search"
  }
}

# Generate Bruno API collection for testing
resource "local_file" "bruno_collection" {
  depends_on = [null_resource.ensure_bruno_dirs]
  filename = "${path.module}/../../build/bruno/RAG-Policy-Search/bruno.json"
  content  = <<-EOT
{
  "version": "1",
  "name": "RAG-Policy-Search",
  "type": "collection",
  "schema": "https://schema.getbruno.io/collection/v1.json",
  "environment": {
    "value": "{{environments.default}}",
    "vars": {}
  },
  "environments": {
    "default": {
      "API_URL": "${aws_apigatewayv2_stage.policy_search_stage.invoke_url}search", 
      "AUTH_TOKEN": "test-token"
    },
    "production": {
      "API_URL": "${aws_apigatewayv2_stage.policy_search_stage.invoke_url}search",
      "AUTH_TOKEN": "YOUR_TOKEN_HERE"
    }
  }
}
EOT
}

resource "local_file" "bruno_search_request" {
  depends_on = [null_resource.ensure_bruno_dirs]
  filename = "${path.module}/../../build/bruno/RAG-Policy-Search/Search Policy.bru"
  content  = <<-EOT
meta {
  name: Search Policy
  type: http
  seq: 1
}

post {
  url: {{API_URL}}
  body: json
  auth: none
}

headers {
  Content-Type: application/json
  Authorization: Bearer {{AUTH_TOKEN}}
}

body:json {
  {
    "query": "What is our password policy?"
  }
}

docs {
  # RAG Policy Search

  This request searches all indexed policy documents using natural language.
  
  The system will:
  1. Convert your query to vector embeddings
  2. Find the most relevant policy chunks in OpenSearch
  3. Use Claude 3 Sonnet to generate a comprehensive answer
  4. Return both the answer and source citations
}
EOT
}

# Generate a README for the Bruno collection
resource "local_file" "bruno_readme" {
  depends_on = [null_resource.ensure_bruno_dirs]
  filename = "${path.module}/../../build/bruno/README.md"
  content  = <<-EOT
# RAG Policy Search API Bruno Collection

This Bruno collection is automatically generated by Terraform with the correct API URL for your deployment.

## API Details

- **API URL**: \`${aws_apigatewayv2_stage.policy_search_stage.invoke_url}search\`
- **Content Type**: application/json
- **Authentication**: Bearer token (placeholder in collection)

## Usage Instructions

1. Open Bruno app
2. Import this collection folder
3. Select the environment (default or production)
4. Use the "Search Policy" request to query the RAG system

## Request Format

```json
{
  "query": "What is our password policy?"
}
```

## Response Format

```json
{
  "query": "What is our password policy?",
  "answer": "Based on the policy excerpts...",
  "sources": [
    {
      "document_name": "Acceptable Encryption Policy",
      "page_number": 3
    }
  ]
}
```

Generated on: $(timestamp())
EOT
}

# Output path to the Bruno collection
output "bruno_collection_path" {
  value       = local_file.bruno_collection.filename
  description = "Path to the generated Bruno collection"
}

# Document tracking outputs
output "document_tracking_table_name" {
  value       = aws_dynamodb_table.document_tracking.name
  description = "The name of the DynamoDB table for document tracking"
}

output "document_tracking_table_arn" {
  value       = aws_dynamodb_table.document_tracking.arn
  description = "The ARN of the DynamoDB table for document tracking"
}

output "sns_topic_arn" {
  value       = aws_sns_topic.document_indexing.arn
  description = "The ARN of the SNS topic for document indexing"
}

output "document_status_api_url" {
  value       = "${aws_apigatewayv2_stage.document_status_stage.invoke_url}/status"
  description = "The URL of the document status API endpoint"
}