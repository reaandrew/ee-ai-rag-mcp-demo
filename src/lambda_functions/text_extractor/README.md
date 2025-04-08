# Text Extractor Lambda Function

This Lambda function extracts text from PDF files uploaded to an S3 bucket. It's triggered automatically on S3 object creation events.

## Function Overview

The Lambda function:

1. Gets triggered when a PDF is uploaded to the configured S3 bucket
2. Extracts text from the PDF (currently a placeholder implementation)
3. Returns extraction results with metadata

## Local Development

To develop and test locally:

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run tests from the project root:
   ```
   pytest tests/lambda/text_extractor
   ```

## Deployment

The function is deployed using Terraform. The main configuration is in `terraform/app/lambda.tf`.

To deploy:

1. Build the Lambda package:
   ```
   make build-lambda
   ```

2. Deploy using Terraform:
   ```
   cd terraform/app
   terraform apply
   ```