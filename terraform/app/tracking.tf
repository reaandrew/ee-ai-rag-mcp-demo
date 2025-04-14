# Attach tracking policies to Lambda roles
resource "aws_iam_role_policy_attachment" "text_chunker_dynamodb_attachment" {
  role       = aws_iam_role.text_chunker_role.name
  policy_arn = aws_iam_policy.dynamodb_access_policy.arn
}

resource "aws_iam_role_policy_attachment" "vector_generator_dynamodb_attachment" {
  role       = aws_iam_role.vector_generator_role.name
  policy_arn = aws_iam_policy.dynamodb_access_policy.arn
}

resource "aws_iam_role_policy_attachment" "text_chunker_sns_attachment" {
  role       = aws_iam_role.text_chunker_role.name
  policy_arn = aws_iam_policy.sns_publish_policy.arn
}

resource "aws_iam_role_policy_attachment" "vector_generator_sns_attachment" {
  role       = aws_iam_role.vector_generator_role.name
  policy_arn = aws_iam_policy.sns_publish_policy.arn
}

# Output is defined in outputs.tf