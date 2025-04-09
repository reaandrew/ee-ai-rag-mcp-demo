# Infrastructure Management

This document provides guidance on managing the AWS infrastructure for this project.

## Infrastructure Components

The project uses the following AWS resources:

- S3 buckets:
  - `ee-ai-rag-mcp-demo-raw-pdfs`: Stores uploaded PDF files
  - `ee-ai-rag-mcp-demo-extracted-text`: Stores text extracted from PDFs
  - `ee-ai-rag-mcp-demo-raw-pdfs-logs`: Stores access logs for the raw PDFs bucket
- Lambda function:
  - `ee-ai-rag-mcp-demo-text-extractor`: Extracts text from PDFs using Amazon Textract
- IAM roles and policies:
  - `ee-ai-rag-mcp-demo-text-extractor-role`: Role for the text extractor Lambda function
  - `ee-ai-rag-mcp-demo-text-extractor-policy`: Policy for the text extractor Lambda function
  - `ee-ai-rag-mcp-demo-ci-role`: Role for CI/CD
- CloudWatch logs
- DynamoDB for Terraform state locking

## Cleaning Up Versioned Infrastructure

If you need to clean up infrastructure that was deployed with versioned bucket names, use the provided cleanup script:

```bash
# Make the script executable if needed
chmod +x cleanup-infrastructure.sh

# Run the script and follow the prompts
./cleanup-infrastructure.sh
```

The script will:
1. Ask for the current version number
2. Empty the versioned S3 buckets
3. Provide instructions for destroying the Terraform infrastructure

## Infrastructure Deployment

The infrastructure is deployed automatically via GitHub Actions when changes are pushed to the main branch. The workflow:

1. Creates a semantic release
2. Sets up Terraform
3. Initializes the backend
4. Applies the Terraform configuration

### Manual Deployment

To manually deploy the infrastructure:

```bash
# Set environment variables
export TF_VAR_app_version=<VERSION>
export TF_VAR_raw_pdfs_bucket_name=ee-ai-rag-mcp-demo-raw-pdfs

# Initialize Terraform
cd terraform/app
terraform init \
  -backend-config="bucket=ee-ai-rag-mcp-demo-terraform-state" \
  -backend-config="key=terraform/app/terraform.tfstate" \
  -backend-config="region=eu-west-2" \
  -backend-config="dynamodb_table=ee-ai-rag-mcp-demo-terraform-locks"

# Plan Terraform changes
terraform plan -out=tfplan

# Apply Terraform changes
terraform apply tfplan
```

## Important Notes

- S3 buckets now use `force_destroy = true` to allow deletion of buckets with objects
- Bucket names no longer include version numbers to prevent issues with bucket cleanup
- The app version is still tracked in resource tags