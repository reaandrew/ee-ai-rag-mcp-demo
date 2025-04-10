#!/bin/bash
set -e

# Initialize Terraform with the correct backend configuration
echo "Initializing Terraform..."
terraform -chdir=terraform/app init \
  -backend-config="bucket=ee-ai-rag-mcp-demo-terraform-state" \
  -backend-config="region=eu-west-2" \
  -backend-config="dynamodb_table=ee-ai-rag-mcp-demo-terraform-locks" \
  -backend-config="key=terraform/app/terraform.tfstate"

# Destroy all infrastructure
echo "Destroying infrastructure..."
terraform -chdir=terraform/app destroy \
  -var="environment=prod" \
  -var="app_version=latest" \
  -var="raw_pdfs_bucket_name=ee-ai-rag-mcp-demo-raw-pdfs" \
  -var="extracted_text_bucket_name=ee-ai-rag-mcp-demo-extracted-text" \
  -var="extracted_text_prefix=ee-ai-rag-mcp-demo" \
  -var="chunked_text_bucket_name=ee-ai-rag-mcp-demo-chunked-text" \
  -var="chunked_text_prefix=ee-ai-rag-mcp-demo" \
  -auto-approve

echo "Infrastructure successfully destroyed!"