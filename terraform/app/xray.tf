# Configure X-Ray tracing for the RAG application - CloudWatch Dashboard only

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
  resource_arn   = "*"  # Match all resources
  version        = 1
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
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-text-extractor", { color: "#2ca02c" }],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-text-chunker", { color: "#1f77b4" }],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-vector-generator", { color: "#ff7f0e" }],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-policy-search", { color: "#d62728" }],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-document-status", { color: "#9467bd" }]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "Lambda Errors",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Sum"
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
            ["AWS/Lambda", "Throttles", "FunctionName", "ee-ai-rag-mcp-demo-text-extractor", { color: "#2ca02c" }],
            ["AWS/Lambda", "Throttles", "FunctionName", "ee-ai-rag-mcp-demo-text-chunker", { color: "#1f77b4" }],
            ["AWS/Lambda", "Throttles", "FunctionName", "ee-ai-rag-mcp-demo-vector-generator", { color: "#ff7f0e" }],
            ["AWS/Lambda", "Throttles", "FunctionName", "ee-ai-rag-mcp-demo-policy-search", { color: "#d62728" }],
            ["AWS/Lambda", "Throttles", "FunctionName", "ee-ai-rag-mcp-demo-document-status", { color: "#9467bd" }]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "Lambda Throttles",
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
            ["AWS/ApiGateway", "Latency", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"],
            ["AWS/ApiGateway", "IntegrationLatency", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "API Gateway Latency",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Average",
          yAxis   = {
            left: { label: "Latency (ms)" }
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
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${aws_dynamodb_table.document_tracking.name}"],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", "${aws_dynamodb_table.document_tracking.name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "DynamoDB Capacity Units",
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
            ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", "${aws_dynamodb_table.document_tracking.name}", "Operation", "GetItem"],
            ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", "${aws_dynamodb_table.document_tracking.name}", "Operation", "PutItem"],
            ["AWS/DynamoDB", "SuccessfulRequestLatency", "TableName", "${aws_dynamodb_table.document_tracking.name}", "Operation", "Query"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "DynamoDB Latency",
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
            ["AWS/S3", "NumberOfObjects", "BucketName", "${var.raw_pdfs_bucket_name}", "StorageType", "AllStorageTypes"],
            ["AWS/S3", "NumberOfObjects", "BucketName", "${var.extracted_text_bucket_name}", "StorageType", "AllStorageTypes"],
            ["AWS/S3", "NumberOfObjects", "BucketName", "${var.chunked_text_bucket_name}", "StorageType", "AllStorageTypes"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "S3 Object Counts",
          region  = data.aws_region.current.name,
          period  = 86400,
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
            ["AWS/SNS", "NumberOfMessagesPublished", "TopicName", "${aws_sns_topic.document_indexing.name}"],
            ["AWS/SNS", "NumberOfNotificationsDelivered", "TopicName", "${aws_sns_topic.document_indexing.name}"],
            ["AWS/SNS", "NumberOfNotificationsFailed", "TopicName", "${aws_sns_topic.document_indexing.name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "SNS Metrics",
          region  = data.aws_region.current.name,
          period  = 300,
          stat    = "Sum"
        }
      }
    ]
  })
}