# S3 bucket for storing raw PDFs
resource "aws_s3_bucket" "raw_pdfs" {
  bucket = var.raw_pdfs_bucket_name

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Enable logging for the raw PDFs bucket
resource "aws_s3_bucket" "logs_bucket" {
  bucket = "${var.raw_pdfs_bucket_name}-logs"

  tags = {
    Environment = var.environment
    Version     = var.app_version
    Description = "Logging bucket for ${var.raw_pdfs_bucket_name}"
  }
}

# Block public access for the raw PDFs bucket - this must come before setting ACLs
resource "aws_s3_bucket_public_access_block" "raw_pdfs_public_access_block" {
  bucket = aws_s3_bucket.raw_pdfs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Block public access for the logs bucket - this must come before setting ACLs
resource "aws_s3_bucket_public_access_block" "logs_bucket_public_access_block" {
  bucket = aws_s3_bucket.logs_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Ownership controls for the logs bucket - required for ACLs in newer AWS provider versions
resource "aws_s3_bucket_ownership_controls" "logs_bucket_ownership" {
  bucket = aws_s3_bucket.logs_bucket.id
  
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Grant log delivery permissions to the logs bucket
resource "aws_s3_bucket_acl" "logs_bucket_acl" {
  # Make sure public access block and ownership are set up first
  depends_on = [
    aws_s3_bucket_public_access_block.logs_bucket_public_access_block,
    aws_s3_bucket_ownership_controls.logs_bucket_ownership
  ]
  
  bucket = aws_s3_bucket.logs_bucket.id
  acl    = "log-delivery-write"
}

# Set up logging for the raw PDFs bucket
resource "aws_s3_bucket_logging" "raw_pdfs_logging" {
  bucket = aws_s3_bucket.raw_pdfs.id

  target_bucket = aws_s3_bucket.logs_bucket.id
  target_prefix = "s3-access-logs/"
}

# Enforce HTTPS-only access to the raw PDFs bucket
resource "aws_s3_bucket_policy" "raw_pdfs_https_only" {
  bucket = aws_s3_bucket.raw_pdfs.id

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "HttpsOnlyPolicy"
    Statement = [
      {
        Sid       = "HttpsOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.raw_pdfs.arn,
          "${aws_s3_bucket.raw_pdfs.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
    ]
  })
}

# Enforce HTTPS-only access to the logs bucket
resource "aws_s3_bucket_policy" "logs_bucket_https_only" {
  # Make sure public access block and ownership are set up first
  depends_on = [
    aws_s3_bucket_public_access_block.logs_bucket_public_access_block,
    aws_s3_bucket_ownership_controls.logs_bucket_ownership
  ]
  
  bucket = aws_s3_bucket.logs_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Id      = "LogsHttpsOnlyPolicy"
    Statement = [
      {
        Sid       = "HttpsOnly"
        Effect    = "Deny"
        Principal = "*"
        Action    = "s3:*"
        Resource = [
          aws_s3_bucket.logs_bucket.arn,
          "${aws_s3_bucket.logs_bucket.arn}/*",
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      },
    ]
  })
}