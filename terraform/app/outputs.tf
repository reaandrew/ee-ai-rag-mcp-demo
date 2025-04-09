output "raw_pdfs_bucket_name" {
  value       = aws_s3_bucket.raw_pdfs.bucket
  description = "The name of the S3 bucket for raw PDFs"
}

output "raw_pdfs_bucket_arn" {
  value       = aws_s3_bucket.raw_pdfs.arn
  description = "The ARN of the S3 bucket for raw PDFs"
}

output "logs_bucket_name" {
  value       = aws_s3_bucket.logs_bucket.bucket
  description = "The name of the S3 bucket for access logs"
}

output "logs_bucket_arn" {
  value       = aws_s3_bucket.logs_bucket.arn
  description = "The ARN of the S3 bucket for access logs"
}

output "deployed_version" {
  value       = var.app_version
  description = "The version of the application that was deployed"
}

output "extracted_text_bucket_name" {
  value       = aws_s3_bucket.extracted_text.bucket
  description = "The name of the S3 bucket for extracted text"
}

output "chunked_text_bucket_name" {
  value       = aws_s3_bucket.chunked_text.bucket
  description = "The name of the S3 bucket for chunked text"
}

output "vector_bucket_name" {
  value       = aws_s3_bucket.vectors.bucket
  description = "The name of the S3 bucket for vector embeddings"
}

output "vector_bucket_arn" {
  value       = aws_s3_bucket.vectors.arn
  description = "The ARN of the S3 bucket for vector embeddings"
}

output "vector_generator_lambda_name" {
  value       = aws_lambda_function.vector_generator.function_name
  description = "The name of the vector generator Lambda function"
}