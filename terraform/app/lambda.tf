# Create IAM role for the text_extractor Lambda function
resource "aws_iam_role" "text_extractor_role" {
  name = "ee-ai-rag-mcp-demo-text-extractor-role"

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

# Create IAM role for the text_chunker Lambda function
resource "aws_iam_role" "text_chunker_role" {
  name = "ee-ai-rag-mcp-demo-text-chunker-role"

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

# Create IAM policy for the text_extractor Lambda function
resource "aws_iam_policy" "text_extractor_policy" {
  name        = "ee-ai-rag-mcp-demo-text-extractor-policy"
  description = "IAM policy for the text extractor Lambda function"

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
          "s3:ListBucket",
          "s3:DeleteObject"  # Permission to delete original PDF
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.raw_pdfs.arn,
          "${aws_s3_bucket.raw_pdfs.arn}/*"
        ]
      },
      {
        Action = [
          "s3:PutObject",    # Permission to write to extracted text bucket
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.extracted_text.arn,
          "${aws_s3_bucket.extracted_text.arn}/*"
        ]
      },
      {
        Action = [
          "textract:DetectDocumentText",
          "textract:AnalyzeDocument",
          "textract:StartDocumentTextDetection",
          "textract:GetDocumentTextDetection"
        ]
        Effect   = "Allow"
        Resource = "*"
      }
    ]
  })
}

# Create IAM policy for the text_chunker Lambda function
resource "aws_iam_policy" "text_chunker_policy" {
  name        = "ee-ai-rag-mcp-demo-text-chunker-policy"
  description = "IAM policy for the text chunker Lambda function"

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
          aws_s3_bucket.extracted_text.arn,
          "${aws_s3_bucket.extracted_text.arn}/*"
        ]
      },
      {
        Action = [
          "s3:PutObject",    # Permission to write to chunked text bucket
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.chunked_text.arn,
          "${aws_s3_bucket.chunked_text.arn}/*"
        ]
      }
    ]
  })
}

# Attach the IAM policy to the text_extractor Lambda function role
resource "aws_iam_role_policy_attachment" "text_extractor_attachment" {
  role       = aws_iam_role.text_extractor_role.name
  policy_arn = aws_iam_policy.text_extractor_policy.arn
}

# Attach the IAM policy to the text_chunker Lambda function role
resource "aws_iam_role_policy_attachment" "text_chunker_attachment" {
  role       = aws_iam_role.text_chunker_role.name
  policy_arn = aws_iam_policy.text_chunker_policy.arn
}

# Reference the pre-built Lambda packages
locals {
  text_extractor_zip_path = "${path.module}/../../build/text-extractor.zip"
  text_chunker_zip_path   = "${path.module}/../../build/text-chunker.zip"
}

# Create the Lambda function
resource "aws_lambda_function" "text_extractor" {
  function_name    = "ee-ai-rag-mcp-demo-text-extractor"
  description      = "Extracts text from uploaded PDF files"
  role             = aws_iam_role.text_extractor_role.arn
  filename         = local.text_extractor_zip_path
  source_code_hash = filebase64sha256(local.text_extractor_zip_path)
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  timeout          = 180  # Increased to 3 minutes to handle async Textract operations
  memory_size      = 512  # Increased to handle larger documents

  environment {
    variables = {
      ENVIRONMENT = var.environment,
      EXTRACTED_TEXT_BUCKET = var.extracted_text_bucket_name,
      EXTRACTED_TEXT_PREFIX = var.extracted_text_prefix,
      DELETE_ORIGINAL_PDF = "true"
    }
  }

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create CloudWatch Log Group for the Lambda function
resource "aws_cloudwatch_log_group" "text_extractor_logs" {
  name              = "/aws/lambda/ee-ai-rag-mcp-demo-text-extractor"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create S3 event notification for the Lambda function
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.raw_pdfs.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.text_extractor.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ".pdf"
  }

  depends_on = [aws_lambda_permission.allow_bucket]
}

# Grant the S3 bucket permission to invoke the Lambda function
resource "aws_lambda_permission" "allow_bucket" {
  statement_id  = "AllowExecutionFromS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.text_extractor.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.raw_pdfs.arn
}

# Create the text_chunker Lambda function
resource "aws_lambda_function" "text_chunker" {
  function_name    = "ee-ai-rag-mcp-demo-text-chunker"
  description      = "Chunks extracted text from text files for RAG applications"
  role             = aws_iam_role.text_chunker_role.arn
  filename         = local.text_chunker_zip_path
  source_code_hash = filebase64sha256(local.text_chunker_zip_path)
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  timeout          = 60   # 1 minute timeout for processing text files
  memory_size      = 256  # 256MB for text chunking

  environment {
    variables = {
      ENVIRONMENT = var.environment,
      CHUNKED_TEXT_BUCKET = var.chunked_text_bucket_name,
      CHUNKED_TEXT_PREFIX = var.chunked_text_prefix,
      CHUNK_SIZE = "1000",           # Default chunk size
      CHUNK_OVERLAP = "200"          # Default chunk overlap
    }
  }

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create CloudWatch Log Group for the text_chunker Lambda function
resource "aws_cloudwatch_log_group" "text_chunker_logs" {
  name              = "/aws/lambda/ee-ai-rag-mcp-demo-text-chunker"
  retention_in_days = 14

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create S3 event notification for the text_chunker Lambda function
resource "aws_s3_bucket_notification" "extracted_text_notification" {
  bucket = aws_s3_bucket.extracted_text.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.text_chunker.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = ""
    filter_suffix       = ".txt"
  }

  depends_on = [aws_lambda_permission.allow_extracted_text_bucket]
}

# Grant the extracted_text S3 bucket permission to invoke the text_chunker Lambda function
resource "aws_lambda_permission" "allow_extracted_text_bucket" {
  statement_id  = "AllowExecutionFromExtractedTextS3Bucket"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.text_chunker.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.extracted_text.arn
}