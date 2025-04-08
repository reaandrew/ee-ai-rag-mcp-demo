provider "aws" {
  region = var.aws_region
}

# Create S3 bucket for Terraform state
resource "aws_s3_bucket" "terraform_state" {
  bucket = var.terraform_state_bucket

  tags = {
    Name        = var.terraform_state_bucket
    Description = "Stores Terraform state for ${var.github_repo}"
    ManagedBy   = "terraform"
  }
}

# Block public access for Terraform state bucket
resource "aws_s3_bucket_public_access_block" "terraform_state_public_access_block" {
  bucket = aws_s3_bucket.terraform_state.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Suspend versioning for the S3 bucket
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  bucket = aws_s3_bucket.terraform_state.id
  
  versioning_configuration {
    status = "Suspended"
  }
}

# Enable default encryption for the terraform state bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_encryption" {
  bucket = aws_s3_bucket.terraform_state.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Create logging bucket for terraform state
resource "aws_s3_bucket" "terraform_state_logs" {
  bucket = "${var.terraform_state_bucket}-logs"

  tags = {
    Name        = "${var.terraform_state_bucket}-logs"
    Description = "Stores access logs for ${var.terraform_state_bucket}"
    ManagedBy   = "terraform"
  }
}

# Block public access for logs bucket
resource "aws_s3_bucket_public_access_block" "terraform_state_logs_public_access_block" {
  bucket = aws_s3_bucket.terraform_state_logs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable default encryption for the terraform state logs bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "terraform_state_logs_encryption" {
  bucket = aws_s3_bucket.terraform_state_logs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Suspend versioning for the terraform state logs bucket
resource "aws_s3_bucket_versioning" "terraform_state_logs_versioning" {
  bucket = aws_s3_bucket.terraform_state_logs.id
  
  versioning_configuration {
    status = "Suspended"
  }
}

# Configure lifecycle rules for the terraform state logs bucket
resource "aws_s3_bucket_lifecycle_configuration" "terraform_state_logs_lifecycle" {
  bucket = aws_s3_bucket.terraform_state_logs.id

  rule {
    id = "expire-old-logs"
    status = "Enabled"
    
    filter {
      prefix = ""  # Empty prefix means apply to all objects
    }

    expiration {
      days = 90
    }
  }
}

# Set ownership controls for logs bucket
resource "aws_s3_bucket_ownership_controls" "terraform_state_logs_ownership" {
  bucket = aws_s3_bucket.terraform_state_logs.id
  
  rule {
    object_ownership = "BucketOwnerPreferred"
  }
}

# Set ACL for logs bucket
resource "aws_s3_bucket_acl" "terraform_state_logs_acl" {
  depends_on = [
    aws_s3_bucket_public_access_block.terraform_state_logs_public_access_block,
    aws_s3_bucket_ownership_controls.terraform_state_logs_ownership
  ]
  
  bucket = aws_s3_bucket.terraform_state_logs.id
  acl    = "log-delivery-write"
}

# Configure logging for terraform state bucket
resource "aws_s3_bucket_logging" "terraform_state_logging" {
  depends_on = [
    aws_s3_bucket_policy.terraform_state_logs_policy,
    aws_s3_bucket_acl.terraform_state_logs_acl
  ]
  
  bucket = aws_s3_bucket.terraform_state.id

  target_bucket = aws_s3_bucket.terraform_state_logs.id
  target_prefix = "state-bucket-logs/"
}


# Combined policy for terraform state logs bucket (includes log delivery and HTTPS enforcement)
resource "aws_s3_bucket_policy" "terraform_state_logs_policy" {
  depends_on = [
    aws_s3_bucket_public_access_block.terraform_state_logs_public_access_block,
    aws_s3_bucket_ownership_controls.terraform_state_logs_ownership,
    aws_s3_bucket_acl.terraform_state_logs_acl
  ]

  bucket = aws_s3_bucket.terraform_state_logs.id

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
          "${aws_s3_bucket.terraform_state_logs.arn}/*"
        ]
      },
      {
        Sid    = "HttpsOnly"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.terraform_state_logs.arn,
          "${aws_s3_bucket.terraform_state_logs.arn}/*"
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

# Apply HTTPS-only policy to terraform state bucket
resource "aws_s3_bucket_policy" "terraform_state_policy" {
  depends_on = [
    aws_s3_bucket_public_access_block.terraform_state_public_access_block,
    aws_s3_bucket_versioning.terraform_state_versioning,
    aws_s3_bucket_server_side_encryption_configuration.terraform_state_encryption
  ]
  
  bucket = aws_s3_bucket.terraform_state.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "HttpsOnly"
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.terraform_state.arn,
          "${aws_s3_bucket.terraform_state.arn}/*"
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



# Create DynamoDB table for Terraform state locking
resource "aws_dynamodb_table" "terraform_lock" {
  name           = var.terraform_lock_table
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "LockID"

  attribute {
    name = "LockID"
    type = "S"
  }

  tags = {
    Name        = var.terraform_lock_table
    Description = "Terraform state locking table for ${var.github_repo}"
    ManagedBy   = "terraform"
  }
}

# Create IAM role for CI/CD
resource "aws_iam_role" "ci_role" {
  name = var.ci_role_name
  
  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Principal = {
          Federated = "arn:aws:iam::${var.aws_account_id}:oidc-provider/token.actions.githubusercontent.com"
        },
        Action = "sts:AssumeRoleWithWebIdentity",
        Condition = {
          StringEquals = {
            "token.actions.githubusercontent.com:aud" = "sts.amazonaws.com"
          },
          StringLike = {
            "token.actions.githubusercontent.com:sub" = [
              "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/main",
              "repo:${var.github_org}/${var.github_repo}:ref:refs/heads/feature/*",
              "repo:${var.github_org}/${var.github_repo}:ref:refs/tags/*"
            ]
          }
        }
      }
    ]
  })

  tags = {
    Description = "Role for GitHub Actions CI/CD to run Terraform"
    ManagedBy   = "terraform"
  }
}

# Create policy for Terraform state management
resource "aws_iam_policy" "terraform_state_policy" {
  name        = "${var.ci_role_name}-state-policy"
  description = "Policy to manage Terraform state in S3 and DynamoDB"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.terraform_state_bucket}",
          "arn:aws:s3:::${var.terraform_state_bucket}/*"
        ]
      },
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:dynamodb:${var.aws_region}:${var.aws_account_id}:table/${var.terraform_lock_table}"
      }
    ]
  })
}

# Create application-specific policies
resource "aws_iam_policy" "app_specific_policy" {
  name        = "${var.ci_role_name}-app-policy"
  description = "Application-specific permissions for the CI role"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        # CloudWatch Logs permissions - expanded to include TagResource and PutRetentionPolicy
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DeleteLogGroup",
          "logs:DeleteLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          "logs:TagResource",
          "logs:UntagResource",
          "logs:ListTagsLogGroup",
          "logs:PutRetentionPolicy"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:${var.aws_region}:${var.aws_account_id}:*"
      },
      {
        # IAM service role permissions - expanded for CI role
        Action = [
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:GetRole",
          "iam:PassRole",
          "iam:TagRole",
          "iam:ListRolePolicies",
          "iam:ListAttachedRolePolicies",
          "iam:CreatePolicy",
          "iam:DeletePolicy",
          "iam:GetPolicy",
          "iam:GetPolicyVersion",
          "iam:ListPolicyVersions",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:TagPolicy"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:iam::${var.aws_account_id}:role/ee-ai-rag-mcp-demo-*",
          "arn:aws:iam::${var.aws_account_id}:policy/ee-ai-rag-mcp-demo-*"
        ]
      },
      {
        # Lambda function permissions - expanded to include permissions management
        Action = [
          "lambda:CreateFunction",
          "lambda:DeleteFunction",
          "lambda:GetFunction",
          "lambda:InvokeFunction",
          "lambda:UpdateFunctionCode",
          "lambda:UpdateFunctionConfiguration",
          "lambda:ListVersionsByFunction",
          "lambda:PublishVersion",
          "lambda:CreateAlias",
          "lambda:DeleteAlias",
          "lambda:UpdateAlias",
          "lambda:GetPolicy",
          "lambda:AddPermission",
          "lambda:RemovePermission",
          "lambda:TagResource",
          "lambda:UntagResource",
          "lambda:ListTags",
          "lambda:GetFunctionCodeSigningConfig"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:lambda:${var.aws_region}:${var.aws_account_id}:function:ee-ai-rag-mcp-demo-*"
      },
      {
        # Lambda service permissions
        Action = [
          "lambda:ListFunctions"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        # Terraform state bucket permissions
        Action = [
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject"
        ]
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::${var.terraform_state_bucket}",
          "arn:aws:s3:::${var.terraform_state_bucket}/*"
        ]
      },
      {
        # Application S3 buckets permissions - allow all S3 operations on specific bucket pattern
        Action = "s3:*"
        Effect   = "Allow"
        Resource = [
          "arn:aws:s3:::ee-ai-rag-mcp-demo-raw-pdfs*",
          "arn:aws:s3:::ee-ai-rag-mcp-demo-raw-pdfs*/*",
          "arn:aws:s3:::${var.terraform_state_bucket}-logs",
          "arn:aws:s3:::${var.terraform_state_bucket}-logs/*"
        ]
      }
    ]
  })
}

# Attach policies to the CI role
resource "aws_iam_role_policy_attachment" "terraform_state_attachment" {
  role       = aws_iam_role.ci_role.name
  policy_arn = aws_iam_policy.terraform_state_policy.arn
}

resource "aws_iam_role_policy_attachment" "app_specific_attachment" {
  role       = aws_iam_role.ci_role.name
  policy_arn = aws_iam_policy.app_specific_policy.arn
}

# Output the role ARN for use in CI setup
output "ci_role_arn" {
  value       = aws_iam_role.ci_role.arn
  description = "ARN of the CI role for GitHub Actions"
}

output "terraform_state_bucket" {
  value       = aws_s3_bucket.terraform_state.bucket
  description = "Name of the S3 bucket for Terraform state"
}

output "terraform_state_logs_bucket" {
  value       = aws_s3_bucket.terraform_state_logs.bucket
  description = "Name of the S3 bucket for Terraform state access logs"
}

output "terraform_lock_table" {
  value       = aws_dynamodb_table.terraform_lock.name
  description = "Name of the DynamoDB table for Terraform state locking"
}