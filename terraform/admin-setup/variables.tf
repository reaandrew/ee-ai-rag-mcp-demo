variable "aws_region" {
  description = "The AWS region to deploy resources into"
  type        = string
  default     = "eu-west-2"
}

variable "aws_account_id" {
  description = "The AWS account ID"
  type        = string
  # No default - must be provided
}

variable "github_org" {
  description = "The GitHub organization or username"
  type        = string
  default     = "reaandrew"
}

variable "github_repo" {
  description = "The GitHub repository name"
  type        = string
  default     = "ee-ai-rag-mcp-demo"
}

variable "terraform_state_bucket" {
  description = "The name of the S3 bucket for Terraform state"
  type        = string
  default     = "ee-ai-rag-mcp-demo-terraform-state"
}

variable "terraform_lock_table" {
  description = "The name of the DynamoDB table for Terraform state locking"
  type        = string
  default     = "ee-ai-rag-mcp-demo-terraform-locks"
}

variable "ci_role_name" {
  description = "The name of the IAM role for CI/CD"
  type        = string
  default     = "ee-ai-rag-mcp-demo-ci-role"
}