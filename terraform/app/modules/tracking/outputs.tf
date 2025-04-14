output "document_tracking_table_name" {
  value = aws_dynamodb_table.document_tracking.name
}

output "document_tracking_table_arn" {
  value = aws_dynamodb_table.document_tracking.arn
}

output "sns_topic_arn" {
  value = aws_sns_topic.document_indexing.arn
}

output "dynamodb_access_policy_arn" {
  value = aws_iam_policy.dynamodb_access_policy.arn
}

output "sns_publish_policy_arn" {
  value = aws_iam_policy.sns_publish_policy.arn
}

output "document_status_api_url" {
  value = "${aws_apigatewayv2_stage.document_status_stage.invoke_url}/status"
}