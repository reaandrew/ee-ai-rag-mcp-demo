# Document tracking module
module "tracking" {
  source      = "./modules/tracking"
  environment = var.environment
  app_version = var.app_version
}

# Attach tracking policies to Lambda roles
resource "aws_iam_role_policy_attachment" "text_chunker_dynamodb_attachment" {
  role       = aws_iam_role.text_chunker_role.name
  policy_arn = module.tracking.dynamodb_access_policy_arn
}

resource "aws_iam_role_policy_attachment" "vector_generator_dynamodb_attachment" {
  role       = aws_iam_role.vector_generator_role.name
  policy_arn = module.tracking.dynamodb_access_policy_arn
}

resource "aws_iam_role_policy_attachment" "text_chunker_sns_attachment" {
  role       = aws_iam_role.text_chunker_role.name
  policy_arn = module.tracking.sns_publish_policy_arn
}

resource "aws_iam_role_policy_attachment" "vector_generator_sns_attachment" {
  role       = aws_iam_role.vector_generator_role.name
  policy_arn = module.tracking.sns_publish_policy_arn
}