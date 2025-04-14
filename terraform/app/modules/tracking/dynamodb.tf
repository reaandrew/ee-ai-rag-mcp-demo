resource "aws_dynamodb_table" "document_tracking" {
  name         = "ee-ai-rag-mcp-demo-doc-tracking"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "document_id"
  
  attribute {
    name = "document_id"
    type = "S"
  }
  
  attribute {
    name = "base_document_id"
    type = "S"
  }
  
  attribute {
    name = "upload_timestamp"
    type = "N"
  }
  
  global_secondary_index {
    name               = "BaseDocumentIndex"
    hash_key           = "base_document_id"
    range_key          = "upload_timestamp"
    projection_type    = "ALL"
  }
  
  ttl {
    attribute_name = "ttl"
    enabled        = true
  }
  
  tags = {
    Environment = var.environment
    Name        = "ee-ai-rag-mcp-demo-document-tracking"
  }
}

# SNS Topic for document indexing notifications
resource "aws_sns_topic" "document_indexing" {
  name = "ee-ai-rag-mcp-demo-document-indexing"
}

# SNS Topic policy to allow Lambda to publish
resource "aws_sns_topic_policy" "document_indexing_policy" {
  arn = aws_sns_topic.document_indexing.arn
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action    = "sns:Publish"
        Effect    = "Allow"
        Resource  = aws_sns_topic.document_indexing.arn
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })
}