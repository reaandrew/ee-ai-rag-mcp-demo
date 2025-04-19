# Add X-Ray tracing to API Gateway

# Enable X-Ray tracing on the default stage of the API Gateway
resource "aws_apigatewayv2_stage" "policy_search_stage_xray" {
  api_id             = aws_apigatewayv2_stage.policy_search_stage.api_id
  name               = "xray-enabled"
  auto_deploy        = true
  
  # Include all the same settings as the original stage
  default_route_settings {
    throttling_burst_limit    = 100
    throttling_rate_limit     = 50
    detailed_metrics_enabled  = true
  }

  # Enable X-Ray tracing
  xray_tracing_enabled = true
  
  depends_on = [aws_apigatewayv2_stage.policy_search_stage]
}