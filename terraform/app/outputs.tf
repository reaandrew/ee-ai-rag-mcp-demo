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