# Lambda layer for document tracking dependencies
resource "aws_lambda_layer_version" "document_tracking_layer" {
  layer_name = "ee-ai-rag-mcp-demo-document-tracking-layer"
  filename   = "${path.module}/../../build/document-tracking-layer.zip"
  source_code_hash = filebase64sha256("${path.module}/../../build/document-tracking-layer.zip")

  compatible_runtimes = ["python3.9"]
  description = "Layer containing dependencies for document_tracking Lambda function"
}

# Document Tracking Lambda - Processes SNS events for document tracking
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
    }
  }

  tags = {
    Environment = var.environment
    Name        = "ee-ai-rag-mcp-demo-document-tracking"
    Service     = "document-tracking"
    ManagedBy   = "terraform"
  }
}

# Lambda deployment package
data "archive_file" "document_tracking_zip" {
  type        = "zip"
  output_path = "${path.module}/build/document_tracking.zip"
  source_dir  = "${path.module}/../../build/document_tracking"
  
  depends_on = [
    null_resource.copy_document_tracking_function
  ]
}

# Copy document tracking function code to build directory
resource "null_resource" "copy_document_tracking_function" {
  triggers = {
    always_run = "${timestamp()}"
  }

  provisioner "local-exec" {
    command = "mkdir -p ${path.module}/../../build/document_tracking && cp -r ${path.module}/../../src/lambda_functions/document_tracking/* ${path.module}/../../build/document_tracking/"
  }
}

# IAM role for document tracking lambda
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
  
  tags = {
    Environment = var.environment
    Name        = "ee-ai-rag-mcp-demo-document-tracking-role"
    Service     = "document-tracking"
    ManagedBy   = "terraform"
  }
}

# SNS subscription for document tracking lambda
resource "aws_sns_topic_subscription" "document_tracking_subscription" {
  topic_arn = aws_sns_topic.document_indexing.arn
  protocol  = "lambda"
  endpoint  = aws_lambda_function.document_tracking.arn
}

# Permission for SNS to invoke the Lambda
resource "aws_lambda_permission" "document_tracking_sns_permission" {
  statement_id  = "AllowExecutionFromSNS"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_tracking.function_name
  principal     = "sns.amazonaws.com"
  source_arn    = aws_sns_topic.document_indexing.arn
}

# DynamoDB access policy attachment for document tracking lambda
resource "aws_iam_role_policy_attachment" "document_tracking_dynamodb_attachment" {
  role       = aws_iam_role.document_tracking_role.name
  policy_arn = aws_iam_policy.dynamodb_access_policy.arn
}

# CloudWatch logs policy for document tracking lambda
resource "aws_iam_policy" "document_tracking_logs_policy" {
  name = "ee-ai-rag-mcp-demo-document-tracking-logs"
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
      }
    ]
  })
}

resource "aws_iam_role_policy_attachment" "document_tracking_logs_attachment" {
  role       = aws_iam_role.document_tracking_role.name
  policy_arn = aws_iam_policy.document_tracking_logs_policy.arn
}