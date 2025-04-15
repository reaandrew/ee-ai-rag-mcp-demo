# S3 bucket for static website hosting
resource "aws_s3_bucket" "ui" {
  bucket = var.ui_bucket_name
  force_destroy = true  # Allow terraform to delete bucket even if it contains objects

  tags = {
    Environment = var.environment
    Name        = "${var.app_name}-ui"
    ManagedBy   = "terraform"
  }
}

# Enable static website hosting on the bucket
resource "aws_s3_bucket_website_configuration" "ui_website" {
  bucket = aws_s3_bucket.ui.id

  index_document {
    suffix = "index.html"
  }

  error_document {
    key = "index.html"
  }
}

# Set ownership controls for the UI bucket
resource "aws_s3_bucket_ownership_controls" "ui_ownership" {
  bucket = aws_s3_bucket.ui.id
  
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Set ACL to public-read for website access
resource "aws_s3_bucket_acl" "ui_acl" {
  depends_on = [
    aws_s3_bucket_ownership_controls.ui_ownership
  ]
  
  bucket = aws_s3_bucket.ui.id
  acl    = "public-read"
}

# Block public access settings - allow read but block write
resource "aws_s3_bucket_public_access_block" "ui_public_access" {
  bucket = aws_s3_bucket.ui.id

  block_public_acls       = false
  block_public_policy     = false
  ignore_public_acls      = false
  restrict_public_buckets = false
}

# Set bucket policy to allow public read access
resource "aws_s3_bucket_policy" "ui_policy" {
  depends_on = [
    aws_s3_bucket_public_access_block.ui_public_access
  ]
  
  bucket = aws_s3_bucket.ui.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "PublicReadGetObject"
        Effect    = "Allow"
        Principal = "*"
        Action    = "s3:GetObject"
        Resource  = [
          "${aws_s3_bucket.ui.arn}/*"
        ]
      }
    ]
  })
}

# Upload index.html file to the bucket
resource "aws_s3_object" "index_html" {
  bucket       = aws_s3_bucket.ui.id
  key          = "index.html"
  source       = "${path.module}/../../ui/index.html"
  content_type = "text/html"
  etag         = filemd5("${path.module}/../../ui/index.html")

  # Make the object publicly readable
  acl          = "public-read"
}

# Output the website URL
output "website_url" {
  value       = "http://${aws_s3_bucket_website_configuration.ui_website.website_endpoint}"
  description = "URL of the static website"
}