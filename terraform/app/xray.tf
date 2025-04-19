# Configure X-Ray tracing for the RAG application

# X-Ray service-linked role
resource "aws_iam_service_linked_role" "xray" {
  aws_service_name = "xray.amazonaws.com"
  description      = "Allows X-Ray to access AWS resources on your behalf"
}

# X-Ray sampling rule for the RAG application
resource "aws_xray_sampling_rule" "ee_ai_rag_mcp_sampling_rule" {
  rule_name      = "ee-ai-rag-mcp-demo-sampling-rule"
  priority       = 1
  reservoir_size = 5
  fixed_rate     = 0.05
  url_path       = "*"
  host           = "*"
  http_method    = "*"
  service_name   = "ee-ai-rag-mcp-demo*"
  service_type   = "*"
  version        = 1
}

# X-Ray encryption key for encrypted trace segments
resource "aws_kms_key" "xray_encryption_key" {
  description             = "KMS key for X-Ray encryption"
  deletion_window_in_days = 30
  enable_key_rotation     = true
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid       = "Enable IAM User Permissions"
        Effect    = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action    = "kms:*"
        Resource  = "*"
      },
      {
        Sid       = "Allow X-Ray to use the key"
        Effect    = "Allow"
        Principal = {
          Service = "xray.amazonaws.com"
        }
        Action    = [
          "kms:GenerateDataKey*",
          "kms:Decrypt"
        ]
        Resource  = "*"
      }
    ]
  })
  
  tags = {
    Environment = var.environment
    Service     = "xray"
  }
}

resource "aws_kms_alias" "xray_key_alias" {
  name          = "alias/ee-ai-rag-mcp-demo-xray"
  target_key_id = aws_kms_key.xray_encryption_key.key_id
}

# X-Ray encryption configuration
resource "aws_xray_encryption_config" "ee_ai_rag_encryption_config" {
  type   = "KMS"
  key_id = aws_kms_key.xray_encryption_key.arn
}

# Add X-Ray permissions to all Lambda IAM roles
locals {
  lambda_role_names = [
    aws_iam_role.text_extractor_role.name,
    aws_iam_role.text_chunker_role.name,
    aws_iam_role.vector_generator_role.name,
    aws_iam_role.policy_search_role.name,
    aws_iam_role.document_status_role.name,
    aws_iam_role.document_tracking_role.name,
    aws_iam_role.auth_authorizer_role.name
  ]
}

# Create X-Ray policy for Lambda functions
resource "aws_iam_policy" "xray_lambda_policy" {
  name        = "ee-ai-rag-mcp-demo-xray-lambda-policy"
  description = "IAM policy for Lambda to use X-Ray tracing across services"
  
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "xray:PutTraceSegments",
          "xray:PutTelemetryRecords",
          "xray:GetSamplingRules",
          "xray:GetSamplingTargets",
          "xray:GetSamplingStatisticSummaries"
        ]
        Effect   = "Allow"
        Resource = "*"
      },
      {
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Effect   = "Allow"
        Resource = aws_kms_key.xray_encryption_key.arn
      }
    ]
  })
}

# Attach X-Ray policy to all Lambda roles
resource "aws_iam_role_policy_attachment" "lambda_xray_policy_attachment" {
  count      = length(local.lambda_role_names)
  role       = local.lambda_role_names[count.index]
  policy_arn = aws_iam_policy.xray_lambda_policy.arn
}

# Update Lambda functions to enable X-Ray tracing
# These modifications extend the existing Lambda function resources
# The format follows the established pattern in the project

# Enable X-Ray for text_extractor Lambda
resource "aws_lambda_function" "text_extractor" {
  # Extend existing resource
  function_name = "ee-ai-rag-mcp-demo-text-extractor"
  
  # Enable X-Ray active tracing
  tracing_config {
    mode = "Active"
  }
}

# Enable X-Ray for text_chunker Lambda
resource "aws_lambda_function" "text_chunker" {
  # Extend existing resource
  function_name = "ee-ai-rag-mcp-demo-text-chunker"
  
  # Enable X-Ray active tracing
  tracing_config {
    mode = "Active"
  }
}

# Enable X-Ray for vector_generator Lambda
resource "aws_lambda_function" "vector_generator" {
  # Extend existing resource
  function_name = "ee-ai-rag-mcp-demo-vector-generator"
  
  # Enable X-Ray active tracing
  tracing_config {
    mode = "Active"
  }
}

# Enable X-Ray for policy_search Lambda
resource "aws_lambda_function" "policy_search" {
  # Extend existing resource
  function_name = "ee-ai-rag-mcp-demo-policy-search"
  
  # Enable X-Ray active tracing
  tracing_config {
    mode = "Active"
  }
}

# Enable X-Ray for document_status Lambda
resource "aws_lambda_function" "document_status" {
  # Extend existing resource
  function_name = "ee-ai-rag-mcp-demo-document-status"
  
  # Enable X-Ray active tracing
  tracing_config {
    mode = "Active"
  }
}

# Enable X-Ray for document_tracking Lambda
resource "aws_lambda_function" "document_tracking" {
  # Extend existing resource
  function_name = "ee-ai-rag-mcp-demo-document-tracking"
  
  # Enable X-Ray active tracing
  tracing_config {
    mode = "Active"
  }
}

# Enable X-Ray for auth_authorizer Lambda
resource "aws_lambda_function" "auth_authorizer" {
  # Extend existing resource
  function_name = "ee-ai-rag-mcp-demo-auth-authorizer"
  
  # Enable X-Ray active tracing
  tracing_config {
    mode = "Active"
  }
}

# Enable X-Ray for API Gateway
resource "aws_apigatewayv2_stage" "policy_search_stage" {
  # Extend existing resource
  api_id = aws_apigatewayv2_api.policy_search_api.id
  name   = "$default"
  
  # Enable X-Ray tracing for API Gateway
  xray_tracing_enabled = true
}

# Add X-Ray Group to organize traces
resource "aws_xray_group" "ee_ai_rag_mcp_xray_group" {
  group_name        = "ee-ai-rag-mcp-demo"
  filter_expression = "service(\"ee-ai-rag-mcp-demo*\")"
}

# Add X-Ray metrics to CloudWatch Dashboard
resource "aws_cloudwatch_dashboard" "xray_dashboard" {
  dashboard_name = "ee-ai-rag-mcp-demo-xray-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# EE AI RAG MCP Demo - X-Ray Tracing Dashboard\nThis dashboard shows end-to-end tracing and metrics for the RAG solution components."
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-text-extractor", { color: "#2ca02c" }],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-text-chunker", { color: "#1f77b4" }],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-vector-generator", { color: "#ff7f0e" }],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-policy-search", { color: "#d62728" }],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-document-status", { color: "#9467bd" }]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "Lambda Invocations",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 2
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-text-extractor", { color: "#2ca02c" }],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-text-chunker", { color: "#1f77b4" }],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-vector-generator", { color: "#ff7f0e" }],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-policy-search", { color: "#d62728" }],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-document-status", { color: "#9467bd" }]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "Lambda Duration (ms)",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 8
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/XRay", "ResponseTime", "Service", "ee-ai-rag-mcp-demo-text-extractor", { color: "#2ca02c" }],
            ["AWS/XRay", "ResponseTime", "Service", "ee-ai-rag-mcp-demo-text-chunker", { color: "#1f77b4" }],
            ["AWS/XRay", "ResponseTime", "Service", "ee-ai-rag-mcp-demo-vector-generator", { color: "#ff7f0e" }],
            ["AWS/XRay", "ResponseTime", "Service", "ee-ai-rag-mcp-demo-policy-search", { color: "#d62728" }],
            ["AWS/XRay", "ResponseTime", "Service", "ee-ai-rag-mcp-demo-document-status", { color: "#9467bd" }]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "X-Ray Response Times",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 8
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/XRay", "ErrorCount", "Service", "ee-ai-rag-mcp-demo-text-extractor", { color: "#2ca02c" }],
            ["AWS/XRay", "ErrorCount", "Service", "ee-ai-rag-mcp-demo-text-chunker", { color: "#1f77b4" }],
            ["AWS/XRay", "ErrorCount", "Service", "ee-ai-rag-mcp-demo-vector-generator", { color: "#ff7f0e" }],
            ["AWS/XRay", "ErrorCount", "Service", "ee-ai-rag-mcp-demo-policy-search", { color: "#d62728" }],
            ["AWS/XRay", "ErrorCount", "Service", "ee-ai-rag-mcp-demo-document-status", { color: "#9467bd" }]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "X-Ray Errors",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"],
            ["AWS/ApiGateway", "4XXError", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"],
            ["AWS/ApiGateway", "5XXError", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "API Gateway Requests",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 14
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/XRay", "ResponseTime", "Service", "API Gateway"],
            ["AWS/XRay", "ErrorCount", "Service", "API Gateway"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "API Gateway X-Ray Metrics",
          region  = data.aws_region.current.name,
          period  = 300,
          yAxis   = {
            left: { label: "Response Time (ms)" },
            right: { label: "Error Count" }
          }
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 20
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/XRay", "ThrottledCount", "Service", "DynamoDB"],
            ["AWS/XRay", "ErrorCount", "Service", "DynamoDB"],
            ["AWS/XRay", "FaultCount", "Service", "DynamoDB"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "DynamoDB X-Ray Metrics",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 20
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/XRay", "ResponseTime", "Service", "DynamoDB"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "DynamoDB X-Ray Response Times",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 26
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/XRay", "ResponseTime", "Service", "S3"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "S3 X-Ray Response Times",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 12
        y      = 26
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/XRay", "ResponseTime", "Service", "SNS"],
            ["AWS/XRay", "ErrorCount", "Service", "SNS"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "SNS X-Ray Metrics",
          region  = data.aws_region.current.name,
          period  = 300,
          yAxis   = {
            left: { label: "Response Time (ms)" },
            right: { label: "Error Count" }
          }
        }
      }
    ]
  })
}