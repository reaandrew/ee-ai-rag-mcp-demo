# S3 bucket for storing raw PDFs
resource "aws_s3_bucket" "raw_pdfs" {
  bucket = var.raw_pdfs_bucket_name
  force_destroy = true  # Allow terraform to delete bucket even if it contains objects

  tags = {
    Environment = var.environment
  }
}

# S3 bucket for storing extracted text
resource "aws_s3_bucket" "extracted_text" {
  bucket = var.extracted_text_bucket_name
  force_destroy = true  # Allow terraform to delete bucket even if it contains objects

  tags = {
    Environment = var.environment
  }
}

# S3 bucket for storing chunked text
resource "aws_s3_bucket" "chunked_text" {
  bucket = var.chunked_text_bucket_name
  force_destroy = true  # Allow terraform to delete bucket even if it contains objects

  tags = {
    Environment = var.environment
  }
}

# Enable logging for the raw PDFs bucket
resource "aws_s3_bucket" "logs_bucket" {
  bucket = "${var.raw_pdfs_bucket_name}-logs"
  force_destroy = true  # Allow terraform to delete bucket even if it contains objects

  tags = {
    Environment = var.environment
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

# Block public access for the extracted text bucket - this must come before setting ACLs
resource "aws_s3_bucket_public_access_block" "extracted_text_public_access_block" {
  bucket = aws_s3_bucket.extracted_text.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Block public access for the chunked text bucket - this must come before setting ACLs
resource "aws_s3_bucket_public_access_block" "chunked_text_public_access_block" {
  bucket = aws_s3_bucket.chunked_text.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable default encryption for the raw PDFs bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "raw_pdfs_encryption" {
  bucket = aws_s3_bucket.raw_pdfs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Enable default encryption for the extracted text bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "extracted_text_encryption" {
  bucket = aws_s3_bucket.extracted_text.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Enable default encryption for the chunked text bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "chunked_text_encryption" {
  bucket = aws_s3_bucket.chunked_text.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}


# Configure lifecycle rules for the raw PDFs bucket
resource "aws_s3_bucket_lifecycle_configuration" "raw_pdfs_lifecycle" {
  bucket = aws_s3_bucket.raw_pdfs.id

  rule {
    id = "archive-old-objects"
    status = "Enabled"
    
    # Add filter block to satisfy the requirement
    filter {
      prefix = ""  # Empty prefix means apply to all objects
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# Configure lifecycle rules for the chunked text bucket
resource "aws_s3_bucket_lifecycle_configuration" "chunked_text_lifecycle" {
  bucket = aws_s3_bucket.chunked_text.id

  rule {
    id = "archive-old-objects"
    status = "Enabled"
    
    # Add filter block to satisfy the requirement
    filter {
      prefix = ""  # Empty prefix means apply to all objects
    }

    transition {
      days          = 30
      storage_class = "STANDARD_IA"
    }

    transition {
      days          = 90
      storage_class = "GLACIER"
    }

    expiration {
      days = 365
    }
  }
}

# Block public access for the logs bucket - this must come before setting ACLs
resource "aws_s3_bucket_public_access_block" "logs_bucket_public_access_block" {
  bucket = aws_s3_bucket.logs_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable default encryption for the logs bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "logs_bucket_encryption" {
  bucket = aws_s3_bucket.logs_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}


# Configure lifecycle rules for the logs bucket
resource "aws_s3_bucket_lifecycle_configuration" "logs_bucket_lifecycle" {
  bucket = aws_s3_bucket.logs_bucket.id

  rule {
    id = "expire-old-logs"
    status = "Enabled"
    
    # Add filter block to satisfy the requirement
    filter {
      prefix = ""  # Empty prefix means apply to all objects
    }

    expiration {
      days = 90
    }
  }
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

# Combined policy for logs bucket (includes log delivery and HTTPS enforcement)
resource "aws_s3_bucket_policy" "logs_bucket_policy" {
  depends_on = [
    aws_s3_bucket_public_access_block.logs_bucket_public_access_block,
    aws_s3_bucket_ownership_controls.logs_bucket_ownership,
    aws_s3_bucket_acl.logs_bucket_acl
  ]

  bucket = aws_s3_bucket.logs_bucket.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "s3-log-delivery"
        Effect = "Allow"
        Principal = {
          Service = "logging.s3.amazonaws.com"
        }
        Action = "s3:PutObject"
        Resource = [
          "${aws_s3_bucket.logs_bucket.arn}/*"
        ]
      },
      {
        Sid    = "HttpsOnly"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.logs_bucket.arn,
          "${aws_s3_bucket.logs_bucket.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Apply HTTPS-only policy to raw PDFs bucket
resource "aws_s3_bucket_policy" "raw_pdfs_policy" {
  depends_on = [
    aws_s3_bucket_public_access_block.raw_pdfs_public_access_block,
    aws_s3_bucket_server_side_encryption_configuration.raw_pdfs_encryption
  ]
  
  bucket = aws_s3_bucket.raw_pdfs.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "HttpsOnly" 
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.raw_pdfs.arn,
          "${aws_s3_bucket.raw_pdfs.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Apply HTTPS-only policy to extracted text bucket
resource "aws_s3_bucket_policy" "extracted_text_policy" {
  depends_on = [
    aws_s3_bucket_public_access_block.extracted_text_public_access_block,
    aws_s3_bucket_server_side_encryption_configuration.extracted_text_encryption
  ]
  
  bucket = aws_s3_bucket.extracted_text.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "HttpsOnly" 
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.extracted_text.arn,
          "${aws_s3_bucket.extracted_text.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}

# Apply HTTPS-only policy to chunked text bucket
resource "aws_s3_bucket_policy" "chunked_text_policy" {
  depends_on = [
    aws_s3_bucket_public_access_block.chunked_text_public_access_block,
    aws_s3_bucket_server_side_encryption_configuration.chunked_text_encryption
  ]
  
  bucket = aws_s3_bucket.chunked_text.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "HttpsOnly" 
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.chunked_text.arn,
          "${aws_s3_bucket.chunked_text.arn}/*"
        ]
        Condition = {
          Bool = {
            "aws:SecureTransport" = "false"
          }
        }
      }
    ]
  })
}


# Set up logging for the raw PDFs bucket
resource "aws_s3_bucket_logging" "raw_pdfs_logging" {
  depends_on = [
    aws_s3_bucket_policy.logs_bucket_policy,
    aws_s3_bucket_acl.logs_bucket_acl
  ]
  
  bucket = aws_s3_bucket.raw_pdfs.id

  target_bucket = aws_s3_bucket.logs_bucket.id
  target_prefix = "raw-pdfs-logs/"
}

