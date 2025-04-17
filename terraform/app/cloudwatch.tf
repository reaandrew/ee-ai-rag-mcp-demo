resource "aws_cloudwatch_dashboard" "ee_ai_rag_dashboard" {
  dashboard_name = "EE-AI-RAG-Dashboard"

  dashboard_body = jsonencode({
    widgets = [
      # Header with system overview
      {
        type   = "text"
        x      = 0
        y      = 0
        width  = 24
        height = 2
        properties = {
          markdown = "# EE AI RAG System Dashboard\nMonitoring for RAG Pipeline, API Performance, AWS Resources, and Error Tracking"
        }
      },

      # Pipeline Performance Section Header
      {
        type   = "text"
        x      = 0
        y      = 2
        width  = 24
        height = 1
        properties = {
          markdown = "## Document Processing Pipeline"
        }
      },

      # Lambda Functions Performance - Invocations
      {
        type   = "metric"
        x      = 0
        y      = 3
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.prefix}-text-extractor"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.prefix}-text-chunker"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.prefix}-vector-generator"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.prefix}-document-tracking"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.prefix}-document-status"],
            ["AWS/Lambda", "Invocations", "FunctionName", "${var.prefix}-policy-search"]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "Lambda Invocations",
          period       = 300,
          stat         = "Sum",
          yAxis        = {
            left = {
              min = 0
            }
          }
        }
      },

      # Lambda Functions Performance - Duration
      {
        type   = "metric"
        x      = 12
        y      = 3
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Duration", "FunctionName", "${var.prefix}-text-extractor"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.prefix}-text-chunker"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.prefix}-vector-generator"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.prefix}-document-tracking"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.prefix}-document-status"],
            ["AWS/Lambda", "Duration", "FunctionName", "${var.prefix}-policy-search"]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "Lambda Duration (ms)",
          period       = 300,
          stat         = "Average",
          yAxis        = {
            left = {
              min = 0
            }
          }
        }
      },

      # Lambda Functions Errors and Throttles
      {
        type   = "metric"
        x      = 0
        y      = 9
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Errors", "FunctionName", "${var.prefix}-text-extractor"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.prefix}-text-chunker"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.prefix}-vector-generator"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.prefix}-document-tracking"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.prefix}-document-status"],
            ["AWS/Lambda", "Errors", "FunctionName", "${var.prefix}-policy-search"]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "Lambda Errors",
          period       = 300,
          stat         = "Sum",
          yAxis        = {
            left = {
              min = 0
            }
          }
        }
      },

      # Lambda Memory Utilization
      {
        type   = "metric"
        x      = 12
        y      = 9
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.prefix}-text-extractor"],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.prefix}-text-chunker"],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.prefix}-vector-generator"],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.prefix}-document-tracking"],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.prefix}-document-status"],
            ["AWS/Lambda", "ConcurrentExecutions", "FunctionName", "${var.prefix}-policy-search"]
          ],
          view         = "timeSeries",
          stacked      = true,
          region       = var.aws_region,
          title        = "Lambda Concurrent Executions",
          period       = 60,
          stat         = "Maximum"
        }
      },

      # OpenSearch/ElasticSearch Section Header
      {
        type   = "text"
        x      = 0
        y      = 15
        width  = 24
        height = 1
        properties = {
          markdown = "## OpenSearch Performance"
        }
      },

      # OpenSearch Cluster Status
      {
        type   = "metric"
        x      = 0
        y      = 16
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ES", "ClusterStatus.green", "DomainName", "${var.prefix}-vectors", { "yAxis" = "left" }],
            ["AWS/ES", "ClusterStatus.yellow", "DomainName", "${var.prefix}-vectors", { "yAxis" = "left" }],
            ["AWS/ES", "ClusterStatus.red", "DomainName", "${var.prefix}-vectors", { "yAxis" = "left" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "OpenSearch Cluster Status",
          period       = 300,
          stat         = "Maximum"
        }
      },

      # OpenSearch CPU and JVM Memory
      {
        type   = "metric"
        x      = 8
        y      = 16
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ES", "CPUUtilization", "DomainName", "${var.prefix}-vectors", { "yAxis" = "left" }],
            ["AWS/ES", "JVMMemoryPressure", "DomainName", "${var.prefix}-vectors", { "yAxis" = "right" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "OpenSearch CPU and JVM",
          period       = 300,
          stat         = "Average",
          yAxis = {
            left = {
              min = 0,
              max = 100
            },
            right = {
              min = 0,
              max = 100
            }
          }
        }
      },

      # OpenSearch Index and Search Performance
      {
        type   = "metric"
        x      = 16
        y      = 16
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ES", "SearchableDocuments", "DomainName", "${var.prefix}-vectors", { "yAxis" = "left" }],
            ["AWS/ES", "SearchLatency", "DomainName", "${var.prefix}-vectors", { "yAxis" = "right" }],
            ["AWS/ES", "IndexingLatency", "DomainName", "${var.prefix}-vectors", { "yAxis" = "right" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "OpenSearch Performance",
          period       = 300,
          stat         = "Average",
          yAxis = {
            right = {
              min = 0
            }
          }
        }
      },

      # DynamoDB Section Header
      {
        type   = "text"
        x      = 0
        y      = 22
        width  = 24
        height = 1
        properties = {
          markdown = "## DynamoDB Performance"
        }
      },

      # DynamoDB Read/Write Capacity
      {
        type   = "metric"
        x      = 0
        y      = 23
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "${var.prefix}-doc-tracking"],
            ["AWS/DynamoDB", "ConsumedWriteCapacityUnits", "TableName", "${var.prefix}-doc-tracking"]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "DynamoDB Consumed Capacity Units",
          period       = 300,
          stat         = "Sum"
        }
      },

      # DynamoDB Throttled Events
      {
        type   = "metric"
        x      = 12
        y      = 23
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/DynamoDB", "ReadThrottleEvents", "TableName", "${var.prefix}-doc-tracking"],
            ["AWS/DynamoDB", "WriteThrottleEvents", "TableName", "${var.prefix}-doc-tracking"]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "DynamoDB Throttled Events",
          period       = 300,
          stat         = "Sum",
          yAxis        = {
            left = {
              min = 0
            }
          }
        }
      },

      # S3 Buckets Section Header
      {
        type   = "text"
        x      = 0
        y      = 29
        width  = 24
        height = 1
        properties = {
          markdown = "## S3 Storage Performance"
        }
      },

      # S3 Bucket Object Count
      {
        type   = "metric"
        x      = 0
        y      = 30
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/S3", "NumberOfObjects", "BucketName", "${var.raw_pdfs_bucket}", "StorageType", "AllStorageTypes", { "label": "Raw PDFs" }],
            ["AWS/S3", "NumberOfObjects", "BucketName", "${var.extracted_text_bucket}", "StorageType", "AllStorageTypes", { "label": "Extracted Text" }],
            ["AWS/S3", "NumberOfObjects", "BucketName", "${var.chunked_text_bucket}", "StorageType", "AllStorageTypes", { "label": "Chunked Text" }],
            ["AWS/S3", "NumberOfObjects", "BucketName", "${var.vectors_bucket}", "StorageType", "AllStorageTypes", { "label": "Vectors" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "S3 Bucket Object Count",
          period       = 86400,
          stat         = "Average"
        }
      },

      # S3 Bucket Size
      {
        type   = "metric"
        x      = 12
        y      = 30
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/S3", "BucketSizeBytes", "BucketName", "${var.raw_pdfs_bucket}", "StorageType", "StandardStorage", { "label": "Raw PDFs" }],
            ["AWS/S3", "BucketSizeBytes", "BucketName", "${var.extracted_text_bucket}", "StorageType", "StandardStorage", { "label": "Extracted Text" }],
            ["AWS/S3", "BucketSizeBytes", "BucketName", "${var.chunked_text_bucket}", "StorageType", "StandardStorage", { "label": "Chunked Text" }],
            ["AWS/S3", "BucketSizeBytes", "BucketName", "${var.vectors_bucket}", "StorageType", "StandardStorage", { "label": "Vectors" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "S3 Bucket Size (Bytes)",
          period       = 86400,
          stat         = "Average"
        }
      },

      # API Gateway Section Header
      {
        type   = "text"
        x      = 0
        y      = 36
        width  = 24
        height = 1
        properties = {
          markdown = "## API Gateway Performance"
        }
      },

      # API Gateway Requests Count
      {
        type   = "metric"
        x      = 0
        y      = 37
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Count", "ApiName", "${var.prefix}-api"]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "API Gateway Request Count",
          period       = 300,
          stat         = "Sum"
        }
      },

      # API Gateway Latency
      {
        type   = "metric"
        x      = 8
        y      = 37
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "Latency", "ApiName", "${var.prefix}-api", { "label": "Overall Latency" }],
            ["AWS/ApiGateway", "IntegrationLatency", "ApiName", "${var.prefix}-api", { "label": "Integration Latency" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "API Gateway Latency (ms)",
          period       = 300,
          stat         = "Average",
          yAxis        = {
            left = {
              min = 0
            }
          }
        }
      },

      # API Gateway Errors
      {
        type   = "metric"
        x      = 16
        y      = 37
        width  = 8
        height = 6
        properties = {
          metrics = [
            ["AWS/ApiGateway", "4XXError", "ApiName", "${var.prefix}-api", { "label": "4XX Errors" }],
            ["AWS/ApiGateway", "5XXError", "ApiName", "${var.prefix}-api", { "label": "5XX Errors" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "API Gateway Errors",
          period       = 300,
          stat         = "Sum",
          yAxis        = {
            left = {
              min = 0
            }
          }
        }
      },

      # AI Services Section Header
      {
        type   = "text"
        x      = 0
        y      = 43
        width  = 24
        height = 1
        properties = {
          markdown = "## AI Service Metrics"
        }
      },

      # Bedrock Service Metrics
      {
        type   = "metric"
        x      = 0
        y      = 44
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Bedrock", "Invocations", "ModelId", "anthropic.claude-3-sonnet-20240229-v1:0", { "label": "Claude 3 Sonnet Invocations" }],
            ["AWS/Bedrock", "Invocations", "ModelId", "amazon.titan-embed-text-v1", { "label": "Titan Embed Invocations" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "Bedrock Model Invocations",
          period       = 300,
          stat         = "Sum"
        }
      },

      # Textract Service Metrics
      {
        type   = "metric"
        x      = 12
        y      = 44
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Textract", "SuccessfulRequestCount", { "label": "Successful Requests" }],
            ["AWS/Textract", "ThrottledCount", { "label": "Throttled Requests" }],
            ["AWS/Textract", "ServerErrorCount", { "label": "Server Errors" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "Textract Requests",
          period       = 300,
          stat         = "Sum"
        }
      },

      # SNS Section Header
      {
        type   = "text"
        x      = 0
        y      = 50
        width  = 24
        height = 1
        properties = {
          markdown = "## SNS Messaging Performance"
        }
      },

      # SNS Metrics
      {
        type   = "metric"
        x      = 0
        y      = 51
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/SNS", "NumberOfMessagesPublished", "TopicName", "${var.prefix}-document-indexing", { "label": "Messages Published" }],
            ["AWS/SNS", "NumberOfNotificationsDelivered", "TopicName", "${var.prefix}-document-indexing", { "label": "Notifications Delivered" }],
            ["AWS/SNS", "NumberOfNotificationsFailed", "TopicName", "${var.prefix}-document-indexing", { "label": "Notifications Failed" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "SNS Message Metrics",
          period       = 300,
          stat         = "Sum"
        }
      },

      # System Overview Metrics
      {
        type   = "metric"
        x      = 12
        y      = 51
        width  = 12
        height = 6
        properties = {
          metrics = [
            ["AWS/Lambda", "Throttles", "FunctionName", "${var.prefix}-text-extractor", { "label": "Text Extractor Throttles" }],
            ["AWS/Lambda", "Throttles", "FunctionName", "${var.prefix}-text-chunker", { "label": "Text Chunker Throttles" }],
            ["AWS/Lambda", "Throttles", "FunctionName", "${var.prefix}-vector-generator", { "label": "Vector Generator Throttles" }],
            ["AWS/Lambda", "Throttles", "FunctionName", "${var.prefix}-policy-search", { "label": "Policy Search Throttles" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = var.aws_region,
          title        = "Lambda Function Throttles",
          period       = 300,
          stat         = "Sum"
        }
      },

      # CloudFront Metrics
      {
        type   = "metric"
        x      = 0
        y      = 57
        width  = 24
        height = 6
        properties = {
          metrics = [
            ["AWS/CloudFront", "Requests", "DistributionId", "YOUR_DISTRIBUTION_ID", "Region", "Global", { "label": "Total Requests" }],
            ["AWS/CloudFront", "TotalErrorRate", "DistributionId", "YOUR_DISTRIBUTION_ID", "Region", "Global", { "label": "Error Rate" }],
            ["AWS/CloudFront", "4xxErrorRate", "DistributionId", "YOUR_DISTRIBUTION_ID", "Region", "Global", { "label": "4xx Error Rate" }],
            ["AWS/CloudFront", "5xxErrorRate", "DistributionId", "YOUR_DISTRIBUTION_ID", "Region", "Global", { "label": "5xx Error Rate" }],
            ["AWS/CloudFront", "BytesDownloaded", "DistributionId", "YOUR_DISTRIBUTION_ID", "Region", "Global", { "label": "Bytes Downloaded" }]
          ],
          view         = "timeSeries",
          stacked      = false,
          region       = "us-east-1",
          title        = "CloudFront Metrics",
          period       = 300,
          stat         = "Sum"
        }
      }
    ]
  })
}

# Add dashboard URL to outputs.tf
# Remember to add: output "cloudwatch_dashboard_url" { value = "https://${var.aws_region}.console.aws.amazon.com/cloudwatch/home?region=${var.aws_region}#dashboards:name=${aws_cloudwatch_dashboard.ee_ai_rag_dashboard.dashboard_name}" }