terraform {
  required_version = ">= 1.0.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
  
  # Note: This configuration intentionally uses local state
  # We can't use S3 backend because we're creating the S3 bucket
  # and DynamoDB table in this Terraform configuration.
  # After the initial apply, you can migrate this state to S3 if desired.
}