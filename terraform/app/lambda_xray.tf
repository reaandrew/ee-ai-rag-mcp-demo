# Modify Lambda configurations to enable X-Ray tracing

# Update the text_extractor Lambda function configuration
resource "aws_lambda_function_configuration" "text_extractor_xray" {
  function_name = aws_lambda_function.text_extractor.function_name
  
  tracing_config {
    mode = "Active"
  }
}

# Update the text_chunker Lambda function configuration
resource "aws_lambda_function_configuration" "text_chunker_xray" {
  function_name = aws_lambda_function.text_chunker.function_name
  
  tracing_config {
    mode = "Active"
  }
}

# Update the vector_generator Lambda function configuration
resource "aws_lambda_function_configuration" "vector_generator_xray" {
  function_name = aws_lambda_function.vector_generator.function_name
  
  tracing_config {
    mode = "Active"
  }
}

# Update the policy_search Lambda function configuration
resource "aws_lambda_function_configuration" "policy_search_xray" {
  function_name = aws_lambda_function.policy_search.function_name
  
  tracing_config {
    mode = "Active"
  }
}

# Update the document_status Lambda function configuration
resource "aws_lambda_function_configuration" "document_status_xray" {
  function_name = aws_lambda_function.document_status.function_name
  
  tracing_config {
    mode = "Active"
  }
}

# Update the document_tracking Lambda function configuration
resource "aws_lambda_function_configuration" "document_tracking_xray" {
  function_name = aws_lambda_function.document_tracking.function_name
  
  tracing_config {
    mode = "Active"
  }
}

# Update the auth_authorizer Lambda function configuration
resource "aws_lambda_function_configuration" "auth_authorizer_xray" {
  function_name = aws_lambda_function.auth_authorizer.function_name
  
  tracing_config {
    mode = "Active"
  }
}