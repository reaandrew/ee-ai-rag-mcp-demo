provider "aws" {
  region = var.aws_region
  
  default_tags {
    tags = {
      Environment = var.environment
      Project     = var.app_name
      Version     = var.app_version
      ManagedBy   = "Terraform"
      Repository  = "github.com/reaandrew/ee-ai-rag-mcp-demo"
    }
  }
}