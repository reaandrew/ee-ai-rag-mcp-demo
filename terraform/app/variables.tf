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

variable "chunked_text_bucket_name" {
  description = "Name of the S3 bucket for storing chunked text"
  type        = string
  default     = "ee-ai-rag-mcp-demo-chunked-text"
}

variable "extracted_text_prefix" {
  description = "Prefix for objects in the extracted text bucket"
  type        = string
  default     = "ee-ai-rag-mcp-demo"
}

variable "chunked_text_prefix" {
  description = "Prefix for objects in the chunked text bucket"
  type        = string
  default     = "ee-ai-rag-mcp-demo"
}

variable "app_version" {
  description = "The application version being deployed"
  type        = string
}

variable "vector_bucket_name" {
  description = "Name of the S3 bucket for storing vector embeddings"
  type        = string
  default     = "ee-ai-rag-mcp-demo-vectors"
}

variable "vector_prefix" {
  description = "Prefix for objects in the vector bucket"
  type        = string
  default     = "ee-ai-rag-mcp-demo"
}

variable "prefix" {
  description = "Prefix for resource naming"
  type        = string
  default     = "ee-ai-rag-mcp-demo"
}

variable "raw_pdfs_bucket" {
  description = "Name of the S3 bucket for storing raw PDFs"
  type        = string
  default     = "ee-ai-rag-mcp-demo-raw-pdfs"
}

variable "extracted_text_bucket" {
  description = "Name of the S3 bucket for storing extracted text"
  type        = string
  default     = "ee-ai-rag-mcp-demo-extracted-text"
}

variable "chunked_text_bucket" {
  description = "Name of the S3 bucket for storing chunked text"
  type        = string
  default     = "ee-ai-rag-mcp-demo-chunked-text"
}

variable "vectors_bucket" {
  description = "Name of the S3 bucket for storing vectors"
  type        = string
  default     = "ee-ai-rag-mcp-demo-vectors"
}

variable "bedrock_model_id" {
  description = "AWS Bedrock model ID to use for generating embeddings"
  type        = string
  default     = "amazon.titan-embed-text-v2:0"
}

variable "opensearch_domain_name" {
  description = "Name of the OpenSearch domain for vector storage"
  type        = string
  default     = "ee-ai-rag-mcp-demo-vectors"
}

variable "opensearch_master_user" {
  description = "Master username for OpenSearch domain"
  type        = string
  default     = "admin"
}

# OpenSearch master password is now handled by random_password resource and stored in Secrets Manager

variable "ui_bucket_name" {
  description = "Name of the S3 bucket for hosting the static website UI"
  type        = string
  default     = "ee-ai-rag-mcp-demo-ui"
}