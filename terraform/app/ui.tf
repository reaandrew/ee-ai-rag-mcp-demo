# S3 bucket for static website hosting
resource "aws_s3_bucket" "ui" {
  bucket = var.ui_bucket_name
  force_destroy = true  # Allow terraform to delete bucket even if it contains objects
  acl = null  # stops the provider sending any PutBucketAcl call

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

# Set ownership controls for the UI bucket (disable ACLs)
resource "aws_s3_bucket_ownership_controls" "ui_ownership" {
  bucket = aws_s3_bucket.ui.id
  
  rule {
    object_ownership = "BucketOwnerEnforced"  # Disables ACLs entirely
  }
}

# Configure public access settings - restricting public access since we're using CloudFront OAC
resource "aws_s3_bucket_public_access_block" "ui_public_access" {
  # Must apply after the bucket and ownership controls are created
  depends_on = [
    aws_s3_bucket.ui,
    aws_s3_bucket_ownership_controls.ui_ownership
  ]
  
  bucket = aws_s3_bucket.ui.id

  # Block public access since we're using CloudFront OAC for secure access
  block_public_acls       = true
  block_public_policy     = false  # Allow bucket policy for CloudFront
  ignore_public_acls      = true
  restrict_public_buckets = false  # Allow bucket policy for CloudFront
}

# This policy is now replaced by ui_policy_cloudfront which restricts access to CloudFront only

# Upload all UI files using the for_each approach with file path lookup
locals {
  # The only ACL S3 will accept with BucketOwnerEnforced
  ui_object_acl = "bucket-owner-full-control"
  
  ui_dir_path = "${path.module}/../../ui"
  content_types = {
    ".html" = "text/html",
    ".css"  = "text/css",
    ".js"   = "application/javascript",
    ".json" = "application/json",
    ".png"  = "image/png",
    ".jpg"  = "image/jpeg",
    ".svg"  = "image/svg+xml",
    ".ico"  = "image/x-icon",
    ".puml" = "text/plain",
  }
}

# Create a file set with all files in the UI directory including subdirectories
resource "terraform_data" "ui_files" {
  provisioner "local-exec" {
    command = "find ${local.ui_dir_path} -type f | sort > ${path.module}/ui_files.txt"
  }
}

# NOTE: UI file deployment has been moved to a separate post-Terraform step
# This allows us to use actual Terraform outputs to populate template variables
# The S3 objects will be uploaded directly using AWS CLI instead of via Terraform

# CloudFront distribution for secure HTTPS access to S3 website
resource "aws_cloudfront_origin_access_control" "ui_oac" {
  name                              = "${var.app_name}-ui-oac"
  description                       = "Origin Access Control for UI S3 bucket"
  origin_access_control_origin_type = "s3"
  signing_behavior                  = "always"
  signing_protocol                  = "sigv4"
}

resource "aws_cloudfront_distribution" "ui_distribution" {
  enabled             = true
  is_ipv6_enabled     = true
  default_root_object = "index.html"
  comment             = "${var.app_name} UI Distribution"
  price_class         = "PriceClass_100" # Use only North America and Europe edge locations to save cost

  # Origin configuration for S3 bucket
  origin {
    domain_name              = aws_s3_bucket.ui.bucket_regional_domain_name
    origin_id                = "S3-${aws_s3_bucket.ui.id}"
    origin_access_control_id = aws_cloudfront_origin_access_control.ui_oac.id
  }

  # Default cache behavior
  default_cache_behavior {
    allowed_methods        = ["GET", "HEAD", "OPTIONS"]
    cached_methods         = ["GET", "HEAD"]
    target_origin_id       = "S3-${aws_s3_bucket.ui.id}"
    viewer_protocol_policy = "redirect-to-https" # Force HTTPS
    min_ttl                = 0
    default_ttl            = 3600  # 1 hour
    max_ttl                = 86400 # 1 day

    # Use managed policy to allow basic S3 static website functionality
    cache_policy_id = "658327ea-f89d-4fab-a63d-7e88639e58f6" # CachingOptimized policy
  }

  # Restrict to specific geographic distributions (optional)
  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  # SSL/TLS certificate - using default CloudFront certificate
  viewer_certificate {
    cloudfront_default_certificate = true
  }

  # Handle 404s with index.html to support SPA routing
  custom_error_response {
    error_code         = 403
    response_code      = 200
    response_page_path = "/index.html"
  }

  custom_error_response {
    error_code         = 404
    response_code      = 200
    response_page_path = "/index.html"
  }

  # Add tags
  tags = {
    Environment = var.environment
    Name        = "${var.app_name}-ui-distribution"
    ManagedBy   = "terraform"
  }
}

# Update bucket policy to allow access only from CloudFront
resource "aws_s3_bucket_policy" "ui_policy_cloudfront" {
  depends_on = [
    aws_s3_bucket_public_access_block.ui_public_access,
    aws_cloudfront_distribution.ui_distribution
  ]
  
  bucket = aws_s3_bucket.ui.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "AllowCloudFrontServicePrincipal"
        Effect    = "Allow"
        Principal = {
          Service = "cloudfront.amazonaws.com"
        }
        Action    = "s3:GetObject"
        Resource  = [
            "${aws_s3_bucket.ui.arn}/index.html",
            "${aws_s3_bucket.ui.arn}/images/*",
            "${aws_s3_bucket.ui.arn}/css/*",
            "${aws_s3_bucket.ui.arn}/js/*",
            "${aws_s3_bucket.ui.arn}/documentation.html"
          ]
        Condition = {
          StringEquals = {
            "AWS:SourceArn" = aws_cloudfront_distribution.ui_distribution.arn
          }
        }
      }
    ]
  })
}

# Output both the direct S3 website URL (HTTP) and CloudFront URL (HTTPS)
output "s3_website_url" {
  value       = "http://${aws_s3_bucket_website_configuration.ui_website.website_endpoint}"
  description = "Direct S3 website URL (HTTP only)"
}

output "cloudfront_url" {
  value       = "https://${aws_cloudfront_distribution.ui_distribution.domain_name}"
  description = "CloudFront distribution URL (HTTPS)"
}

output "ui_bucket_name" {
  value       = aws_s3_bucket.ui.bucket
  description = "Name of the S3 bucket hosting the UI"
}