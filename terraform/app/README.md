# Application Terraform Configuration

This directory contains the Terraform configuration that will be applied by the CI/CD pipeline when a new version is released.

## Structure

Add your application's Terraform configuration files here. At minimum, you should include:

1. `main.tf` - Main configuration for your application resources
2. `variables.tf` - Variable definitions
3. `outputs.tf` - Output definitions
4. `terraform.tf` - Provider and backend configuration

## Backend Configuration

The backend configuration should be set up to use the S3 bucket and DynamoDB table created by the admin Terraform:

```hcl
terraform {
  backend "s3" {
    # These values will be provided dynamically in CI
    # bucket         = "ee-ai-rag-mcp-demo-terraform-state"
    # key            = "terraform/app/terraform.tfstate"
    # region         = "eu-west-2"
    # dynamodb_table = "ee-ai-rag-mcp-demo-terraform-locks"
  }
}
```

The actual values will be injected during the CI process from repository secrets.