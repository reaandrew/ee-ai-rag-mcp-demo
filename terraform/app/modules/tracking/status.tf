# IAM role for the document_status Lambda function
resource "aws_iam_role" "document_status_role" {
  name = "ee-ai-rag-mcp-demo-document-status-role"

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
  }
}

# IAM policy for the document_status Lambda function
resource "aws_iam_policy" "document_status_policy" {
  name        = "ee-ai-rag-mcp-demo-document-status-policy"
  description = "IAM policy for the document status Lambda function"

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
          "dynamodb:Query"
        ]
        Effect   = "Allow"
        Resource = aws_dynamodb_table.document_tracking.arn
      }
    ]
  })
}

# Attach policy to role
resource "aws_iam_role_policy_attachment" "document_status_attachment" {
  role       = aws_iam_role.document_status_role.name
  policy_arn = aws_iam_policy.document_status_policy.arn
}

# Package the document_status Lambda function
data "archive_file" "document_status_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda_functions/document_status"
  output_path = "${path.module}/../../build/document-status.zip"
}

# Create the Lambda function
resource "aws_lambda_function" "document_status" {
  function_name    = "ee-ai-rag-mcp-demo-document-status"
  description      = "Returns document processing status"
  role             = aws_iam_role.document_status_role.arn
  filename         = data.archive_file.document_status_zip.output_path
  source_code_hash = data.archive_file.document_status_zip.output_base64sha256
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  timeout          = 30
  memory_size      = 128

  environment {
    variables = {
      ENVIRONMENT    = var.environment,
      TRACKING_TABLE = aws_dynamodb_table.document_tracking.name
    }
  }

  tags = {
    Environment = var.environment
  }
}

# CloudWatch Log Group for the Lambda function
resource "aws_cloudwatch_log_group" "document_status_logs" {
  name              = "/aws/lambda/${aws_lambda_function.document_status.function_name}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
  }
}

# API Gateway for document status
resource "aws_apigatewayv2_api" "document_status_api" {
  name          = "ee-ai-rag-mcp-demo-document-status-api"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["GET", "POST", "OPTIONS"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 300
  }
}

# API Gateway stage
resource "aws_apigatewayv2_stage" "document_status_stage" {
  api_id      = aws_apigatewayv2_api.document_status_api.id
  name        = "$default"
  auto_deploy = true
}

# API Gateway integration
resource "aws_apigatewayv2_integration" "document_status_integration" {
  api_id                 = aws_apigatewayv2_api.document_status_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.document_status.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# API Gateway routes
resource "aws_apigatewayv2_route" "document_status_route" {
  api_id    = aws_apigatewayv2_api.document_status_api.id
  route_key = "GET /status"
  target    = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
}

resource "aws_apigatewayv2_route" "document_status_path_route" {
  api_id    = aws_apigatewayv2_api.document_status_api.id
  route_key = "GET /status/{document_id}"
  target    = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
}

resource "aws_apigatewayv2_route" "document_status_post_route" {
  api_id    = aws_apigatewayv2_api.document_status_api.id
  route_key = "POST /status"
  target    = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
}

resource "aws_apigatewayv2_route" "document_status_options_route" {
  api_id    = aws_apigatewayv2_api.document_status_api.id
  route_key = "OPTIONS /status"
  target    = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "document_status_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_status.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.document_status_api.execution_arn}/*/*"
}