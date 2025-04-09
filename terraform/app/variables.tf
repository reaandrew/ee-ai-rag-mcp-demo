variable "aws_region" {
  description = "The AWS region to deploy resources into"
  type        = string
  default     = "eu-west-2"
}

variable "app_name" {
  description = "The name of the application"
  type        = string
  default     = "ee-ai-rag-mcp-demo"
}

variable "environment" {
  description = "The deployment environment (e.g., dev, test, prod)"
  type        = string
  default     = "dev"
}

variable "raw_pdfs_bucket_name" {
  description = "Name of the S3 bucket for storing raw PDFs"
  type        = string
  default     = "ee-ai-rag-mcp-demo-raw-pdfs"
}

variable "extracted_text_bucket_name" {
  description = "Name of the S3 bucket for storing extracted text"
  type        = string
  default     = "ee-ai-rag-mcp-demo-extracted-text"
}

variable "extracted_text_prefix" {
  description = "Prefix for objects in the extracted text bucket"
  type        = string
  default     = "ee-ai-rag-mcp-demo"
}

variable "app_version" {
  description = "The application version being deployed"
  type        = string
}