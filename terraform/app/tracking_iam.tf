resource "aws_iam_policy" "dynamodb_access_policy" {
  name = "ee-ai-rag-mcp-demo-dynamodb-access"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "dynamodb:PutItem",
          "dynamodb:GetItem",
          "dynamodb:UpdateItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Effect   = "Allow"
        Resource = [
          aws_dynamodb_table.document_tracking.arn,
          "${aws_dynamodb_table.document_tracking.arn}/index/BaseDocumentIndex"
        ]
      }
    ]
  })
}

resource "aws_iam_policy" "sns_publish_policy" {
  name = "ee-ai-rag-mcp-demo-sns-publish"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action   = ["sns:Publish"]
        Effect   = "Allow"
        Resource = [aws_sns_topic.document_indexing.arn]
      },
      {
        Action = [
          "kms:Decrypt",
          "kms:GenerateDataKey*"
        ]
        Effect   = "Allow"
        Resource = aws_kms_key.sns_encryption_key.arn
      }
    ]
  })
}