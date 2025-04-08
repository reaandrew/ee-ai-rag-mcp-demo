# Text Extractor Lambda Function

This Lambda function extracts text from PDF files uploaded to an S3 bucket using AWS Textract. It's triggered automatically on S3 object creation events.

## Function Overview

The Lambda function:

1. Gets triggered when a PDF is uploaded to the configured S3 bucket
2. Uses AWS Textract to extract text from the PDF
3. Handles both small documents (synchronous API) and large documents (asynchronous API)
4. Returns extraction results with metadata and the full extracted text

## AWS Textract Integration

This Lambda function leverages AWS Textract to extract text from PDF documents. 

Key features:

- **Smart Document Processing**: Uses Textract's machine learning to accurately extract text
- **Auto-Switching**: Uses the efficient synchronous API for small documents (≤5 pages)
- **Async Handling**: Automatically switches to asynchronous API for larger documents
- **Pagination Support**: Handles multi-page documents with proper text ordering
- **Robust Error Handling**: Includes timeout management, error recovery, and detailed logging

## Required Permissions

The Lambda function requires specific IAM permissions to interact with Textract:

- `textract:DetectDocumentText` - For synchronous text extraction
- `textract:StartDocumentTextDetection` - For initiating asynchronous jobs
- `textract:GetDocumentTextDetection` - For retrieving results from async jobs
- `textract:AnalyzeDocument` - For additional document analysis capabilities

## Local Development

To develop and test locally:

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Run tests from the project root:
   ```
   pytest tests/lambda_functions/text_extractor
   ```

3. For local Textract testing, ensure you have AWS credentials configured with Textract permissions

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

## Response Format

The Lambda function returns a structured JSON response:

```json
{
  "statusCode": 200,
  "body": {
    "message": "Extracted text from 1 PDF files",
    "results": [
      {
        "source": {
          "bucket": "bucket-name",
          "file_key": "document.pdf",
          "size_bytes": 123456,
          "last_modified": "2025-04-08 12:34:56+00:00",
          "content_type": "application/pdf"
        },
        "extracted_text": "The full extracted text content...",
        "page_count": 3,
        "status": "success"
      }
    ]
  }
}
```