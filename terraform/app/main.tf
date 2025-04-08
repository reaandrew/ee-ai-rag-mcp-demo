# S3 bucket for storing raw PDFs
resource "aws_s3_bucket" "raw_pdfs" {
  bucket = var.raw_pdfs_bucket_name

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}