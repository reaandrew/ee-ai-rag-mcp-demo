# Admin Terraform Setup

This directory contains Terraform configuration that needs to be applied by an admin (not in CI) to set up the necessary infrastructure for CI/CD pipeline to run Terraform.

## What This Creates

1. An S3 bucket for storing Terraform state
2. A DynamoDB table for Terraform state locking
3. An IAM role with a trust policy for GitHub Actions
4. IAM policies that allow the CI role to:
   - Access the Terraform state (S3 bucket and DynamoDB)
   - Deploy application resources

## Prerequisites

- AWS CLI configured with admin credentials
- Terraform installed locally
- GitHub OIDC provider must be set up in your AWS account

## Setup GitHub OIDC Provider

Before running this Terraform, ensure you have the GitHub OIDC provider set up in your AWS account:

```bash
aws iam create-open-id-connect-provider \
  --url https://token.actions.githubusercontent.com \
  --client-id-list sts.amazonaws.com \
  --thumbprint-list 6938fd4d98bab03faadb97b34396831e3780aea1
```

## Usage

1. Create a `terraform.tfvars` file with your account details:

```hcl
aws_account_id       = "your-aws-account-id"
aws_region           = "eu-west-2"
github_org           = "reaandrew"
github_repo          = "ee-ai-rag-mcp-demo"
terraform_state_bucket = "ee-ai-rag-mcp-demo-terraform-state"
terraform_lock_table = "ee-ai-rag-mcp-demo-terraform-locks"
ci_role_name         = "ee-ai-rag-mcp-demo-ci-role"
```

2. Initialize Terraform:

```bash
terraform init
```

3. Apply the configuration:

```bash
terraform plan
terraform apply
```

4. Note the outputs:
   - `ci_role_arn` - Use this in your GitHub Actions workflow
   - `terraform_state_bucket` - For the S3 backend in your Terraform configurations
   - `terraform_lock_table` - For state locking in your Terraform configurations

## Using in CI Workflows

Once the infrastructure is set up, your CI workflows can use the assume role with web identity to authenticate with AWS:

```yaml
jobs:
  terraform:
    runs-on: ubuntu-latest
    permissions:
      id-token: write
      contents: read
    steps:
      - uses: actions/checkout@v3
      
      - name: Configure AWS Credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          role-to-assume: ${{ secrets.CI_ROLE_ARN }}
          aws-region: eu-west-2
          
      - name: Setup Terraform
        uses: hashicorp/setup-terraform@v2
        
      # ... terraform init, plan, apply steps
```