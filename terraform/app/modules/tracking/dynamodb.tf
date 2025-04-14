# Get current AWS account ID
data "aws_caller_identity" "current" {}

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
  
  # Enable server-side encryption with AWS managed key
  server_side_encryption {
    enabled = true
  }
  
  # Enable point-in-time recovery for enhanced data protection
  point_in_time_recovery {
    enabled = true
  }
  
  tags = {
    Environment = var.environment
    Name        = "ee-ai-rag-mcp-demo-document-tracking"
    Service     = "document-tracking"
    ManagedBy   = "terraform"
  }
}

# KMS key for SNS topic encryption
resource "aws_kms_key" "sns_encryption_key" {
  description             = "KMS key for SNS topic encryption"
  deletion_window_in_days = 10
  enable_key_rotation     = true
  
  tags = {
    Environment = var.environment
    Name        = "ee-ai-rag-mcp-demo-sns-encryption-key"
  }
}

resource "aws_kms_alias" "sns_encryption_key_alias" {
  name          = "alias/ee-ai-rag-mcp-demo-sns-encryption"
  target_key_id = aws_kms_key.sns_encryption_key.key_id
}

# KMS key policy for SNS to use the key
resource "aws_kms_key_policy" "sns_key_policy" {
  key_id = aws_kms_key.sns_encryption_key.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "Allow SNS to use the key"
        Effect = "Allow"
        Principal = {
          Service = "sns.amazonaws.com"
        }
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Resource = "*"
      },
      {
        Sid    = "Allow key management"
        Effect = "Allow"
        Principal = {
          AWS = "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
        }
        Action = "kms:*"
        Resource = "*"
      }
    ]
  })
}

# SNS Topic for document indexing notifications with encryption
resource "aws_sns_topic" "document_indexing" {
  name              = "ee-ai-rag-mcp-demo-document-indexing"
  kms_master_key_id = aws_kms_key.sns_encryption_key.id
  
  tags = {
    Environment = var.environment
    Name        = "ee-ai-rag-mcp-demo-document-indexing"
  }
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
  
  # Associate the topic policy with the topic
  # Note: This explicit dependency isn't necessary but helps clarify the relationship
  depends_on = [aws_sns_topic.document_indexing]
}