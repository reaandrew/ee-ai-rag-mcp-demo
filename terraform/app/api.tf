# API Gateway and Lambda for policy search queries

# Create IAM role for the policy_search Lambda function
resource "aws_iam_role" "policy_search_role" {
  name = "ee-ai-rag-mcp-demo-policy-search-role"

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

# Create IAM policy for the policy_search Lambda function
resource "aws_iam_policy" "policy_search_policy" {
  name        = "ee-ai-rag-mcp-demo-policy-search-policy"
  description = "IAM policy for the policy search Lambda function"

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
          "bedrock:InvokeModel"  # Permission to invoke Bedrock models for embeddings and LLM
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

# Attach the IAM policy to the policy_search Lambda function role
resource "aws_iam_role_policy_attachment" "policy_search_attachment" {
  role       = aws_iam_role.policy_search_role.name
  policy_arn = aws_iam_policy.policy_search_policy.arn
}

# Lambda layer for policy_search dependencies
resource "aws_lambda_layer_version" "policy_search_layer" {
  layer_name = "ee-ai-rag-mcp-demo-policy-search-layer"
  filename   = "${path.module}/../../build/policy-search-layer.zip"
  source_code_hash = filebase64sha256("${path.module}/../../build/policy-search-layer.zip")

  compatible_runtimes = ["python3.9"]
  description = "Layer containing dependencies for policy_search Lambda function"
}

# Package the policy_search Lambda function
data "archive_file" "policy_search_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda_functions/policy_search"
  output_path = "${path.module}/../../build/policy-search.zip"
}

# Create the policy_search Lambda function
resource "aws_lambda_function" "policy_search" {
  function_name    = "ee-ai-rag-mcp-demo-policy-search"
  description      = "Searches policies using natural language queries"
  role             = aws_iam_role.policy_search_role.arn
  filename         = data.archive_file.policy_search_zip.output_path
  source_code_hash = data.archive_file.policy_search_zip.output_base64sha256
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  timeout          = 30   # 30 seconds timeout for handling queries
  memory_size      = 512  # 512MB for processing

  # Use the policy_search layer for dependencies
  layers           = [aws_lambda_layer_version.policy_search_layer.arn]

  environment {
    variables = {
      ENVIRONMENT = var.environment,
      OPENSEARCH_DOMAIN = var.opensearch_domain_name,
      OPENSEARCH_ENDPOINT = aws_opensearch_domain.vectors.endpoint,
      OPENSEARCH_INDEX = "rag-vectors",
      EMBEDDING_MODEL_ID = var.bedrock_model_id,
      LLM_MODEL_ID = "anthropic.claude-3-sonnet-20240229-v1:0",
      USE_IAM_AUTH = "true",
      USE_AOSS = "false"
    }
  }

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create CloudWatch Log Group for the policy_search Lambda function
resource "aws_cloudwatch_log_group" "policy_search_logs" {
  name              = "/aws/lambda/${aws_lambda_function.policy_search.function_name}"
  retention_in_days = 30  # 30 days retention for security compliance

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create IAM role for the auth_authorizer Lambda function
resource "aws_iam_role" "auth_authorizer_role" {
  name = "ee-ai-rag-mcp-demo-auth-authorizer-role"

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

# Create IAM policy for the auth_authorizer Lambda function
resource "aws_iam_policy" "auth_authorizer_policy" {
  name        = "ee-ai-rag-mcp-demo-auth-authorizer-policy"
  description = "IAM policy for the API Gateway authorizer Lambda function"

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

# Attach the IAM policy to the auth_authorizer role
resource "aws_iam_role_policy_attachment" "auth_authorizer_attachment" {
  role       = aws_iam_role.auth_authorizer_role.name
  policy_arn = aws_iam_policy.auth_authorizer_policy.arn
}

# Package the auth_authorizer Lambda function
data "archive_file" "auth_authorizer_zip" {
  type        = "zip"
  source_dir  = "${path.module}/../../src/lambda_functions/auth_authorizer"
  output_path = "${path.module}/../../build/auth-authorizer.zip"
}

# Create the auth_authorizer Lambda function
resource "aws_lambda_function" "auth_authorizer" {
  function_name    = "ee-ai-rag-mcp-demo-auth-authorizer"
  description      = "Lambda authorizer for API Gateway"
  role             = aws_iam_role.auth_authorizer_role.arn
  filename         = data.archive_file.auth_authorizer_zip.output_path
  source_code_hash = data.archive_file.auth_authorizer_zip.output_base64sha256
  handler          = "handler.lambda_handler"
  runtime          = "python3.9"
  timeout          = 10   # 10 seconds timeout for authorizer
  memory_size      = 128  # 128MB is sufficient for an authorizer

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

# Create CloudWatch Log Group for the auth_authorizer Lambda function
resource "aws_cloudwatch_log_group" "auth_authorizer_logs" {
  name              = "/aws/lambda/${aws_lambda_function.auth_authorizer.function_name}"
  retention_in_days = 30  # 30 days retention for security compliance

  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create API Gateway for the policy search endpoint
resource "aws_apigatewayv2_api" "policy_search_api" {
  name          = "ee-ai-rag-mcp-demo-policy-search-api"
  protocol_type = "HTTP"
  
  cors_configuration {
    allow_origins = ["*"]
    allow_methods = ["POST"]
    allow_headers = ["content-type", "authorization"]
    max_age       = 300
  }
}

# Create CloudWatch log group for API Gateway
resource "aws_cloudwatch_log_group" "api_gateway_logs" {
  name              = "/aws/apigateway/ee-ai-rag-mcp-demo-policy-search-api"
  retention_in_days = 30  # 30 days retention for security compliance
  
  tags = {
    Environment = var.environment
    Version     = var.app_version
  }
}

# Create CloudWatch logs resource policy for API Gateway
resource "aws_cloudwatch_log_resource_policy" "api_gateway_log_policy" {
  policy_name     = "ee-ai-rag-mcp-demo-api-gateway-log-policy"
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
        Resource  = "${aws_cloudwatch_log_group.api_gateway_logs.arn}:*"
      }
    ]
  })
}

# Create API Gateway stage with logging enabled
resource "aws_apigatewayv2_stage" "policy_search_stage" {
  api_id      = aws_apigatewayv2_api.policy_search_api.id
  name        = "$default"
  auto_deploy = true
  
  # Ensure log group and policy are created first
  depends_on = [
    aws_cloudwatch_log_group.api_gateway_logs,
    aws_cloudwatch_log_resource_policy.api_gateway_log_policy
  ]
  
  access_log_settings {
    destination_arn = aws_cloudwatch_log_group.api_gateway_logs.arn
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
}

# Create Lambda authorizer for API Gateway
resource "aws_apigatewayv2_authorizer" "lambda_authorizer" {
  api_id           = aws_apigatewayv2_api.policy_search_api.id
  authorizer_type  = "REQUEST"
  authorizer_uri   = aws_lambda_function.auth_authorizer.invoke_arn
  identity_sources = ["$request.header.Authorization"]
  name             = "lambda-authorizer"
  authorizer_payload_format_version = "2.0"
  enable_simple_responses = true
}

# Create API Gateway integration with Lambda
resource "aws_apigatewayv2_integration" "policy_search_integration" {
  api_id                 = aws_apigatewayv2_api.policy_search_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.policy_search.invoke_arn
  integration_method     = "POST"
  payload_format_version = "2.0"
}

# Create API Gateway route with authorizer
resource "aws_apigatewayv2_route" "policy_search_route" {
  api_id             = aws_apigatewayv2_api.policy_search_api.id
  route_key          = "POST /search"
  target             = "integrations/${aws_apigatewayv2_integration.policy_search_integration.id}"
  authorizer_id      = aws_apigatewayv2_authorizer.lambda_authorizer.id
  authorization_type = "CUSTOM"
}

# Grant API Gateway permission to invoke the policy_search Lambda function
resource "aws_lambda_permission" "api_gateway_policy_search" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.policy_search.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.policy_search_api.execution_arn}/*/*/search"
}

# Grant API Gateway permission to invoke the auth_authorizer Lambda function
resource "aws_lambda_permission" "api_gateway_auth_authorizer" {
  statement_id  = "AllowExecutionFromAPIGateway"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.auth_authorizer.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.policy_search_api.execution_arn}/authorizers/*"
}

# Output the API Gateway URL
output "policy_search_api_url" {
  value = "${aws_apigatewayv2_stage.policy_search_stage.invoke_url}search"
  description = "The URL of the policy search API endpoint"
}