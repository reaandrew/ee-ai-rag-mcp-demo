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
        Condition = {
          StringEquals = {
            "aws:SourceAccount": data.aws_caller_identity.current.account_id
          }
        }
      }
    ]
  })

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "document-tracking"
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
        Resource = [
          "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/ee-ai-rag-mcp-demo-document-status:*",
          "arn:aws:logs:${data.aws_region.current.name}:${data.aws_caller_identity.current.account_id}:log-group:/aws/lambda/ee-ai-rag-mcp-demo-document-status"
        ]
      },
      {
        Action = [
          "dynamodb:GetItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = [
          aws_dynamodb_table.document_tracking.arn,
          "${aws_dynamodb_table.document_tracking.arn}/index/BaseDocumentIndex"
        ]
      }
    ]
  })
  
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "document-tracking"
  }
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

# Lambda layer for document status dependencies
resource "aws_lambda_layer_version" "document_status_layer" {
  layer_name = "ee-ai-rag-mcp-demo-document-status-layer"
  filename   = "${path.module}/../../build/document-status-layer.zip"
  source_code_hash = filebase64sha256("${path.module}/../../build/document-status-layer.zip")

  compatible_runtimes = ["python3.9"]
  description = "Layer containing dependencies for document_status Lambda function"
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
  layers           = [aws_lambda_layer_version.document_status_layer.arn]

  environment {
    variables = {
      ENVIRONMENT    = var.environment,
      TRACKING_TABLE = aws_dynamodb_table.document_tracking.name
    }
  }

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "document-tracking"
    Version     = var.app_version
  }
}

# CloudWatch Log Group for the Lambda function
resource "aws_cloudwatch_log_group" "document_status_logs" {
  name              = "/aws/lambda/${aws_lambda_function.document_status.function_name}"
  retention_in_days = 30

  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "document-tracking"
  }
}

# Use the existing API Gateway instead of creating a new one
# The policy_search_api already has CORS configured

# API Gateway integration for document status using existing API Gateway
resource "aws_apigatewayv2_integration" "document_status_integration" {
  api_id                 = aws_apigatewayv2_api.policy_search_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.document_status.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
  
  # Enable timeouts for improved security
  timeout_milliseconds   = 29000  # 29 seconds, just under Lambda's 30-second timeout
  
  # Connection settings
  connection_type        = "INTERNET"  # Direct connection to Lambda
  description            = "Integration with document status Lambda function"
}

# API Gateway route for document status using existing API
resource "aws_apigatewayv2_route" "document_status_route" {
  api_id             = aws_apigatewayv2_api.policy_search_api.id
  route_key          = "GET /status"
  target             = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
  authorizer_id      = aws_apigatewayv2_authorizer.lambda_authorizer.id
  authorization_type = "CUSTOM"
}

# OPTIONS route with authorizer for security compliance
resource "aws_apigatewayv2_route" "document_status_options_route" {
  api_id             = aws_apigatewayv2_api.policy_search_api.id
  route_key          = "OPTIONS /status"
  target             = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
  authorizer_id      = aws_apigatewayv2_authorizer.lambda_authorizer.id
  authorization_type = "CUSTOM"
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "document_status_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_status.function_name
  principal     = "apigateway.amazonaws.com"
  
  # Source ARN for the existing API Gateway
  source_arn    = "${aws_apigatewayv2_api.policy_search_api.execution_arn}/*/*/status*"
  
  # Adding source account condition for enhanced security
  source_account = data.aws_caller_identity.current.account_id
}

# API URL is defined in outputs.tf