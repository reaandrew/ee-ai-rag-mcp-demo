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

# Enable versioning for the S3 bucket
resource "aws_s3_bucket_versioning" "terraform_state_versioning" {
  bucket = aws_s3_bucket.terraform_state.id
  
  versioning_configuration {
    status = "Enabled"
  }
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
        Action = [
          # Lambda permissions
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
          
          # IAM permissions for service roles
          "iam:GetRole",
          "iam:PassRole",
          "iam:CreateRole",
          "iam:DeleteRole",
          "iam:AttachRolePolicy",
          "iam:DetachRolePolicy",
          "iam:PutRolePolicy",
          "iam:DeleteRolePolicy",
          "iam:GetRolePolicy",
          
          # API Gateway permissions
          "apigateway:*",
          
          # CloudWatch Logs permissions
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:DeleteLogGroup",
          "logs:DeleteLogStream",
          "logs:DescribeLogGroups",
          "logs:DescribeLogStreams",
          "logs:PutLogEvents",
          
          # S3 permissions for application buckets
          "s3:CreateBucket",
          "s3:DeleteBucket",
          "s3:ListBucket",
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:PutBucketPolicy",
          "s3:GetBucketPolicy",
          
          # CloudFormation for Terraform
          "cloudformation:DescribeStacks",
          "cloudformation:ListStacks",
          "cloudformation:CreateStack",
          "cloudformation:DeleteStack",
          "cloudformation:DescribeStackEvents",
          "cloudformation:UpdateStack",
          "cloudformation:GetTemplate"
        ]
        Effect   = "Allow"
        Resource = "*"
        # Note: This is a broad policy for demonstration. In practice, you should scope permissions more narrowly.
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

output "terraform_lock_table" {
  value       = aws_dynamodb_table.terraform_lock.name
  description = "Name of the DynamoDB table for Terraform state locking"
}