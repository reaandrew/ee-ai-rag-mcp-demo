# Generate a random password for the OpenSearch master user
resource "random_password" "opensearch_master_password" {
  length           = 16
  special          = true
  override_special = "!#$%&*()-_=+[]{}<>:?"
}

# Store the OpenSearch master credentials in AWS Secrets Manager
resource "aws_secretsmanager_secret" "opensearch_master_credentials" {
  name                    = "ee-ai-rag-mcp-demo/opensearch-master-credentials"
  description             = "Master credentials for the OpenSearch domain"
  force_overwrite_replica = true
  recovery_window_in_days = 0  # Immediately delete without recovery window
  
  tags = {
    Environment = var.environment
    Name        = "ee-ai-rag-mcp-demo-opensearch-credentials"
  }
}

# Store the OpenSearch master credentials as a JSON string
resource "aws_secretsmanager_secret_version" "opensearch_credentials" {
  secret_id = aws_secretsmanager_secret.opensearch_master_credentials.id
  secret_string = jsonencode({
    username = var.opensearch_master_user
    password = random_password.opensearch_master_password.result
  })
}

# OpenSearch domain for vector storage
resource "aws_opensearch_domain" "vectors" {
  domain_name    = var.opensearch_domain_name
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
      master_user_password = random_password.opensearch_master_password.result
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
        Resource = "arn:aws:es:${var.aws_region}:${data.aws_caller_identity.current.account_id}:domain/${var.opensearch_domain_name}/*"
      }
    ]
  })

  tags = {
    Environment = var.environment
    Name        = var.opensearch_domain_name
  }
}

# The permissions to read from Secrets Manager are included in the main vector_generator policy

# Get current AWS account details
data "aws_caller_identity" "current" {}