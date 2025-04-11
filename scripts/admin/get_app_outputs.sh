#!/usr/bin/env bash


terraform init \
  -backend-config="bucket=ee-ai-rag-mcp-demo-terraform-state" \
  -backend-config="key=terraform/app/terraform.tfstate" \
  -backend-config="region=eu-west-2" \
  -backend-config="dynamodb_table=ee-ai-rag-mcp-demo-terraform-locks"

terraform output
