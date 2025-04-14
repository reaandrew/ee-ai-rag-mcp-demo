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
          "dynamodb:Query"
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
  
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "document-tracking"
  }
}

# Create CloudWatch log group for API Gateway
resource "aws_cloudwatch_log_group" "document_status_api_logs" {
  name              = "/aws/apigateway/ee-ai-rag-mcp-demo-document-status-api"
  retention_in_days = 30  # 30 days retention for security compliance
  
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "document-tracking"
  }
}

# Create CloudWatch logs resource policy for API Gateway
resource "aws_cloudwatch_log_resource_policy" "document_status_api_log_policy" {
  policy_name     = "ee-ai-rag-mcp-demo-document-status-api-log-policy"
  policy_document = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect    = "Allow"
        Principal = {
          Service = "apigateway.amazonaws.com"
        }
        Action    = [
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ]
        Resource  = "${aws_cloudwatch_log_group.document_status_api_logs.arn}:*"
      }
    ]
  })
}

# API Gateway stage with logging enabled
resource "aws_apigatewayv2_stage" "document_status_stage" {
  api_id      = aws_apigatewayv2_api.document_status_api.id
  name        = "$default"
  auto_deploy = true
  
  # Ensure log group and policy are created first
  depends_on = [
    aws_cloudwatch_log_group.document_status_api_logs,
    aws_cloudwatch_log_resource_policy.document_status_api_log_policy
  ]
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.document_status_api_logs.arn
    format = jsonencode({
      requestId      = "$context.requestId"
      ip             = "$context.identity.sourceIp"
      requestTime    = "$context.requestTime"
      httpMethod     = "$context.httpMethod"
      routeKey       = "$context.routeKey"
      status         = "$context.status"
      protocol       = "$context.protocol"
      responseLength = "$context.responseLength"
      integrationError = "$context.integrationErrorMessage"
      error          = "$context.error.message"
      errorResponseType = "$context.error.responseType"
      path           = "$context.path"
    })
  }
  
  default_route_settings {
    detailed_metrics_enabled = true
    throttling_burst_limit   = 100
    throttling_rate_limit    = 50
  }
  
  tags = {
    Environment = var.environment
    ManagedBy   = "terraform"
    Service     = "document-tracking"
  }
}

# API Gateway integration with improved security
resource "aws_apigatewayv2_integration" "document_status_integration" {
  api_id                 = aws_apigatewayv2_api.document_status_api.id
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

# Get the existing Lambda authorizer
data "aws_apigatewayv2_authorizer" "lambda_authorizer" {
  api_id = var.api_gateway_id
  authorizer_id = var.authorizer_id
}

# API Gateway routes with authorizer
resource "aws_apigatewayv2_route" "document_status_route" {
  api_id             = aws_apigatewayv2_api.document_status_api.id
  route_key          = "GET /status"
  target             = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
  authorizer_id      = var.authorizer_id
  authorization_type = "CUSTOM"
}

resource "aws_apigatewayv2_route" "document_status_path_route" {
  api_id             = aws_apigatewayv2_api.document_status_api.id
  route_key          = "GET /status/{document_id}"
  target             = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
  authorizer_id      = var.authorizer_id
  authorization_type = "CUSTOM"
}

resource "aws_apigatewayv2_route" "document_status_post_route" {
  api_id             = aws_apigatewayv2_api.document_status_api.id
  route_key          = "POST /status"
  target             = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
  authorizer_id      = var.authorizer_id
  authorization_type = "CUSTOM"
}

# OPTIONS request doesn't need authorization (for CORS preflight)
resource "aws_apigatewayv2_route" "document_status_options_route" {
  api_id    = aws_apigatewayv2_api.document_status_api.id
  route_key = "OPTIONS /status"
  target    = "integrations/${aws_apigatewayv2_integration.document_status_integration.id}"
}

# Lambda permission for API Gateway with more specific source ARN
resource "aws_lambda_permission" "document_status_permission" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.document_status.function_name
  principal     = "apigateway.amazonaws.com"
  
  # More specific source ARN for improved security
  source_arn    = "${aws_apigatewayv2_api.document_status_api.execution_arn}/*/*/status*"
  
  # Adding source account condition for enhanced security
  source_account = data.aws_caller_identity.current.account_id
}