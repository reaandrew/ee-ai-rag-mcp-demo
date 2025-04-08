# Create IAM role for the Lambda function
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

# Create IAM policy for the Lambda function
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
          "s3:ListBucket"
        ]
        Effect = "Allow"
        Resource = [
          aws_s3_bucket.raw_pdfs.arn,
          "${aws_s3_bucket.raw_pdfs.arn}/*"
        ]
      }
    ]
  })
}

# Attach the IAM policy to the Lambda function role
resource "aws_iam_role_policy_attachment" "text_extractor_attachment" {
  role       = aws_iam_role.text_extractor_role.name
  policy_arn = aws_iam_policy.text_extractor_policy.arn
}

# Package the Lambda function
data "archive_file" "text_extractor_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda/text_extractor"
  output_path = "${path.module}/../../build/text-extractor.zip"
}

# Create the Lambda function
resource "aws_lambda_function" "text_extractor" {
  function_name    = "ee-ai-rag-mcp-demo-text-extractor"
  description      = "Extracts text from uploaded PDF files"
  role             = aws_iam_role.text_extractor_role.arn
  filename         = data.archive_file.text_extractor_zip.output_path
  source_code_hash = data.archive_file.text_extractor_zip.output_base64sha256
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      ENVIRONMENT = var.environment
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