# S3 bucket for storing vector embeddings
resource "aws_s3_bucket" "vectors" {
  bucket = var.vector_bucket_name
  force_destroy = true  # Allow terraform to delete bucket even if it contains objects

  tags = {
    Environment = var.environment
  }
}

# Block public access for the vectors bucket - this must come before setting ACLs
resource "aws_s3_bucket_public_access_block" "vectors_public_access_block" {
  bucket = aws_s3_bucket.vectors.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Enable default encryption for the vectors bucket
resource "aws_s3_bucket_server_side_encryption_configuration" "vectors_encryption" {
  bucket = aws_s3_bucket.vectors.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Configure lifecycle rules for the vectors bucket
resource "aws_s3_bucket_lifecycle_configuration" "vectors_lifecycle" {
  bucket = aws_s3_bucket.vectors.id

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

# Apply HTTPS-only policy to vectors bucket
resource "aws_s3_bucket_policy" "vectors_policy" {
  depends_on = [
    aws_s3_bucket_public_access_block.vectors_public_access_block,
    aws_s3_bucket_server_side_encryption_configuration.vectors_encryption
  ]
  
  bucket = aws_s3_bucket.vectors.id
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "HttpsOnly" 
        Effect = "Deny"
        Principal = "*"
        Action = "s3:*"
        Resource = [
          aws_s3_bucket.vectors.arn,
          "${aws_s3_bucket.vectors.arn}/*"
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

# Create IAM role for the vector_generator Lambda function
resource "aws_iam_role" "vector_generator_role" {
  name = "ee-ai-rag-mcp-demo-vector-generator-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create IAM policy for the vector_generator Lambda function
resource "aws_iam_policy" "vector_generator_policy" {
  name        = "ee-ai-rag-mcp-demo-vector-generator-policy"
  description = "IAM policy for the vector generator Lambda function"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Effect   = "Allow"
        Resource = "arn:aws:logs:*:*:*"
      },
      {
        Action = [
          "s3:GetObject",
          "s3:HeadObject",
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.chunked_text.arn,
          "${aws_s3_bucket.chunked_text.arn}/*"
        ]
      },
      {
        Action = [
          "bedrock:InvokeModel"  # Permission to invoke Bedrock models
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "es:ESHttpGet",
          "es:ESHttpPost",
          "es:ESHttpPut",
          "es:ESHttpDelete",
          "es:ESHttpHead",
          "es:DescribeDomain",
          "es:ListDomainNames",
          "opensearch:ESHttpGet",
          "opensearch:ESHttpPost",
          "opensearch:ESHttpPut",
          "opensearch:ESHttpDelete",
          "opensearch:ESHttpHead",
          "opensearch:DescribeDomain",
          "opensearch:ListDomainNames"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.opensearch_domain_name}/*",
          "arn:aws:opensearch:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.opensearch_domain_name}/*"
        ]
      },
      {
        Action = [
          "aoss:APIAccessAll",
          "aoss:CreateIndex",
          "aoss:DeleteIndex",
          "aoss:UpdateIndex",
          "aoss:CreateCollection",
          "aoss:BatchGetCollection",
          "aoss:ListCollections",
          "aoss:BatchGetVpcEndpoint",
          "aoss:ListAccessPolicies",
          "aoss:ListSecurityConfigs",
          "aoss:ListSecurityPolicies",
          "aoss:ListVpcEndpoints"
        ]
        Effect = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "secretsmanager:GetSecretValue",
          "secretsmanager:DescribeSecret"
        ]
        Effect = "Allow"
        Resource = [
          "arn:aws:secretsmanager:${var.aws_region}:${data.aws_caller_identity.current.account_id}:secret:ee-ai-rag-mcp-demo/opensearch-master-credentials*"
        ]
      }
    ]
  })
}

# Attach the IAM policy to the vector_generator Lambda function role
resource "aws_iam_role_policy_attachment" "vector_generator_attachment" {
  role       = aws_iam_role.vector_generator_role.name
  policy_arn = aws_iam_policy.vector_generator_policy.arn
}

# Package the vector_generator Lambda function
data "archive_file" "vector_generator_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda_functions/vector_generator"
  output_path = "${path.module}/../../build/vector-generator.zip"
}

# Lambda layer for vector_generator dependencies
resource "aws_lambda_layer_version" "vector_generator_layer" {
  layer_name = "ee-ai-rag-mcp-demo-vector-generator-layer"
  filename   = "${path.module}/../../build/vector-generator-layer.zip"
  source_code_hash = filebase64sha256("${path.module}/../../build/vector-generator-layer.zip")

  compatible_runtimes = ["python3.9"]
  description = "Layer containing dependencies for vector_generator Lambda function"
}

# Create the vector_generator Lambda function
resource "aws_lambda_function" "vector_generator" {
  function_name    = "ee-ai-rag-mcp-demo-vector-generator"
  description      = "Generates vector embeddings from chunked text using AWS Bedrock"
  role             = aws_iam_role.vector_generator_role.arn
  filename         = data.archive_file.vector_generator_zip.output_path
  source_code_hash = data.archive_file.vector_generator_zip.output_base64sha256
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60   # 1 minute timeout for processing chunks
  memory_size      = 256  # 256MB for vector generation
  layers           = [aws_lambda_layer_version.vector_generator_layer.arn]

  environment {
    variables = {
      ENVIRONMENT = var.environment,
      CHUNKED_TEXT_BUCKET = var.chunked_text_bucket_name,
      OPENSEARCH_DOMAIN = var.opensearch_domain_name,
      OPENSEARCH_ENDPOINT = aws_opensearch_domain.vectors.endpoint,
      OPENSEARCH_INDEX = "rag-vectors",
      VECTOR_PREFIX = var.vector_prefix,
      MODEL_ID = var.bedrock_model_id,
      USE_IAM_AUTH = "true",
      USE_AOSS = "false",  # Set to "true" if using OpenSearch Serverless
      TRACKING_TABLE = aws_dynamodb_table.document_tracking.name,
      SNS_TOPIC_ARN = aws_sns_topic.document_indexing.arn
    }
  }

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create CloudWatch Log Group for the vector_generator Lambda function
resource "aws_cloudwatch_log_group" "vector_generator_logs" {
  name              = "/aws/lambda/ee-ai-rag-mcp-demo-vector-generator"
  retention_in_days = 30  # 30 days retention for security compliance

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create S3 event notification for the vector_generator Lambda function
resource "aws_s3_bucket_notification" "chunked_text_notification" {
  bucket = aws_s3_bucket.chunked_text.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.vector_generator.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ".json"
  }

  depends_on = [aws_lambda_permission.allow_chunked_text_bucket]
}

# Grant the chunked_text S3 bucket permission to invoke the vector_generator Lambda function
resource "aws_lambda_permission" "allow_chunked_text_bucket" {
  statement_id  = "AllowExecutionFromChunkedTextS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.vector_generator.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.chunked_text.arn
}