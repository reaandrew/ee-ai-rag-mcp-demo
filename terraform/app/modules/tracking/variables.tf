variable "environment" {
  description = "Environment name"
  type        = string
}

variable "app_version" {
  description = "Application version"
  type        = string
}

variable "api_gateway_id" {
  description = "ID of the existing API Gateway that contains the authorizer"
  type        = string
}

variable "authorizer_id" {
  description = "ID of the Lambda authorizer to use for API routes"
  type        = string
}