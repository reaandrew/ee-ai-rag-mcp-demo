resource "aws_cloudwatch_dashboard" "ee_ai_rag_mcp_dashboard" {
  dashboard_name = "ee-ai-rag-mcp-demo-dashboard"
  
  dashboard_body = jsonencode({
    widgets = [
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# EE AI RAG MCP Demo Application Dashboard\nThis dashboard shows the performance and metrics for the RAG application components."
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 2
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-text-extractor"],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-text-chunker"],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-vector-generator"],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-policy-search"],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-document-status"],
            ["AWS/Lambda", "Invocations", "FunctionName", "ee-ai-rag-mcp-demo-document-tracking"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "Lambda Invocations",
          region  = "us-east-1",
          period  = 300,
          stat    = "Sum"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 2
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-text-extractor"],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-text-chunker"],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-vector-generator"],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-policy-search"],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-document-status"],
            ["AWS/Lambda", "Duration", "FunctionName", "ee-ai-rag-mcp-demo-document-tracking"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "Lambda Duration (ms)",
          region  = "us-east-1",
          period  = 300,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 2
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-text-extractor"],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-text-chunker"],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-vector-generator"],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-policy-search"],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-document-status"],
            ["AWS/Lambda", "Errors", "FunctionName", "ee-ai-rag-mcp-demo-document-tracking"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "Lambda Errors",
          region  = "us-east-1",
          period  = 300,
          stat    = "Sum"
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
            ["AWS/ApiGateway", "Count", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"],
            ["AWS/ApiGateway", "4XXError", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"],
            ["AWS/ApiGateway", "5XXError", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "API Gateway Requests",
          region  = "us-east-1",
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
            ["AWS/ApiGateway", "Latency", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"],
            ["AWS/ApiGateway", "IntegrationLatency", "ApiId", "${aws_apigatewayv2_api.policy_search_api.id}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "API Gateway Latency",
          region  = "us-east-1",
          period  = 300,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 0
        y      = 14
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/S3", "BucketSizeBytes", "StorageType", "StandardStorage", "BucketName", "${var.raw_pdfs_bucket_name}"],
            ["AWS/S3", "BucketSizeBytes", "StorageType", "StandardStorage", "BucketName", "${var.extracted_text_bucket_name}"],
            ["AWS/S3", "BucketSizeBytes", "StorageType", "StandardStorage", "BucketName", "${var.chunked_text_bucket_name}"],
            ["AWS/S3", "BucketSizeBytes", "StorageType", "StandardStorage", "BucketName", "${var.vector_bucket_name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "S3 Bucket Sizes",
          region  = "us-east-1",
          period  = 86400,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 8
        y      = 14
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/S3", "NumberOfObjects", "StorageType", "AllStorageTypes", "BucketName", "${var.raw_pdfs_bucket_name}"],
            ["AWS/S3", "NumberOfObjects", "StorageType", "AllStorageTypes", "BucketName", "${var.extracted_text_bucket_name}"],
            ["AWS/S3", "NumberOfObjects", "StorageType", "AllStorageTypes", "BucketName", "${var.chunked_text_bucket_name}"],
            ["AWS/S3", "NumberOfObjects", "StorageType", "AllStorageTypes", "BucketName", "${var.vector_bucket_name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "S3 Object Counts",
          region  = "us-east-1",
          period  = 86400,
          stat    = "Average"
        }
      },
      {
        type   = "metric"
        x      = 16
        y      = 14
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${aws_dynamodb_table.document_tracking.name}"],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", "${aws_dynamodb_table.document_tracking.name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "DynamoDB Capacity Units",
          region  = "us-east-1",
          period  = 300,
          stat    = "Sum"
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
            ["AWS/SNS", "NumberOfMessagesPublished", "TopicName", "${aws_sns_topic.document_indexing.name}"],
            ["AWS/SNS", "NumberOfNotificationsDelivered", "TopicName", "${aws_sns_topic.document_indexing.name}"],
            ["AWS/SNS", "NumberOfNotificationsFailed", "TopicName", "${aws_sns_topic.document_indexing.name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "SNS Metrics",
          region  = "us-east-1",
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
            ["AWS/ES", "ClusterStatus.green", "DomainName", "${var.opensearch_domain_name}"],
            ["AWS/ES", "ClusterStatus.yellow", "DomainName", "${var.opensearch_domain_name}"],
            ["AWS/ES", "ClusterStatus.red", "DomainName", "${var.opensearch_domain_name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "OpenSearch Cluster Status",
          region  = "us-east-1",
          period  = 300,
          stat    = "Maximum",
          yAxis = {
            left = {
              min = 0,
              max = 1
            }
          }
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
            ["AWS/ES", "CPUUtilization", "DomainName", "${var.opensearch_domain_name}"],
            ["AWS/ES", "JVMMemoryPressure", "DomainName", "${var.opensearch_domain_name}"],
            ["AWS/ES", "FreeStorageSpace", "DomainName", "${var.opensearch_domain_name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "OpenSearch Resource Utilization",
          region  = "us-east-1",
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
            ["AWS/ES", "SearchableDocuments", "DomainName", "${var.opensearch_domain_name}"],
            ["AWS/ES", "SearchRate", "DomainName", "${var.opensearch_domain_name}"],
            ["AWS/ES", "IndexingRate", "DomainName", "${var.opensearch_domain_name}"]
          ],
          view    = "timeSeries",
          stacked = false,
          title   = "OpenSearch Operations",
          region  = "us-east-1",
          period  = 300,
          stat    = "Average"
        }
      }
    ]
  })
}