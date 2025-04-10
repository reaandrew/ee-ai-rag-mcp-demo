# OpenSearch domain for vector storage
resource "aws_opensearch_domain" "vectors" {
  domain_name    = "ee-ai-rag-mcp-demo-vectors"
  engine_version = "OpenSearch_2.9"

  cluster_config {
    instance_type          = "t3.small.search" # More cost-effective instance for dev
    instance_count         = 1
    zone_awareness_enabled = false
  }

  ebs_options {
    ebs_enabled = true
    volume_size = 10
  }

  encrypt_at_rest {
    enabled = true
  }

  node_to_node_encryption {
    enabled = true
  }

  domain_endpoint_options {
    enforce_https       = true
    tls_security_policy = "Policy-Min-TLS-1-2-2019-07"
  }

  advanced_security_options {
    enabled                        = true
    internal_user_database_enabled = true
    master_user_options {
      master_user_name     = var.opensearch_master_user
      master_user_password = var.opensearch_master_password
    }
  }

  # Access control policy for domain
  access_policies = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          AWS = aws_iam_role.vector_generator_role.arn
        }
        Action   = "es:*"
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/ee-ai-rag-mcp-demo-vectors/*"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = "ee-ai-rag-mcp-demo-vectors"
  }
}

# Get current AWS account details
data "aws_caller_identity" "current" {}