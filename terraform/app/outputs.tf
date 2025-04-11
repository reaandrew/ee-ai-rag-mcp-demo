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