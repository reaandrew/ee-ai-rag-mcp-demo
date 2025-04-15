# Document Tracking Lambda
# This Lambda subscribes to SNS topics and handles updates to the DynamoDB tracking table

# Lambda source code and dependencies
data "archive_file" "document_tracking_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda_functions/document_tracking"
  output_path = "${path.module}/../../package/document_tracking.zip"
}

# Lambda layer for dependencies
resource "aws_lambda_layer_version" "document_tracking_layer" {
  layer_name          = "ee-ai-rag-mcp-demo-document-tracking-layer"
  filename            = "${path.module}/../../package/document_tracking_layer.zip"
  source_code_hash    = filebase64sha256("${path.module}/../../package/document_tracking_layer.zip")
  compatible_runtimes = ["python3.9"]
  description         = "Dependencies for document tracking Lambda function"
}

# Document Tracking Lambda function
resource "aws_lambda_function" "document_tracking" {
  function_name    = "ee-ai-rag-mcp-demo-document-tracking"
  filename         = data.archive_file.document_tracking_zip.output_path
  source_code_hash = data.archive_file.document_tracking_zip.output_base64sha256
  role             = aws_iam_role.document_tracking_role.arn
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  timeout          = 30
  memory_size      = 256
  layers           = [aws_lambda_layer_version.document_tracking_layer.arn]

  environment {
    variables = {
      TRACKING_TABLE = aws_dynamodb_table.document_tracking.name
      SNS_TOPIC_ARN  = aws_sns_topic.document_indexing.arn
    }
  }
}

# IAM role for Document Tracking Lambda
resource "aws_iam_role" "document_tracking_role" {
  name = "ee-ai-rag-mcp-demo-document-tracking-role"

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
}

# IAM policy for Document Tracking Lambda
resource "aws_iam_policy" "document_tracking_policy" {
  name        = "ee-ai-rag-mcp-demo-document-tracking-policy"
  description = "IAM policy for document tracking Lambda function"

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
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.document_tracking.arn
      },
      {
        Action = [
          "dynamodb:Query"
        ]
        Effect   = "Allow"
        Resource = "${aws_dynamodb_table.document_tracking.arn}/index/BaseDocumentIndex"
      },
      {
        Action = [
          "sns:Publish",
          "sns:Subscribe"
        ]
        Effect   = "Allow"
        Resource = aws_sns_topic.document_indexing.arn
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "document_tracking_policy_attachment" {
  role       = aws_iam_role.document_tracking_role.name
  policy_arn = aws_iam_policy.document_tracking_policy.arn
}

# SNS subscription for document tracking lambda
resource "aws_sns_topic_subscription" "document_tracking_subscription" {
  topic_arn = aws_sns_topic.document_indexing.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.document_tracking.arn
}

# Lambda permission for SNS invocation
resource "aws_lambda_permission" "document_tracking_sns_permission" {
  statement_id  = "AllowSNSInvocation"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_tracking.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.document_indexing.arn
}