# Testing the Text Extractor Lambda Function

This document explains how to test the text extractor Lambda function using the provided Python scripts.

## Prerequisites

1. AWS CLI configured with appropriate permissions
2. Python 3.6+ installed
3. Required Python packages:
   ```
   pip install boto3
   ```
4. For the full script with PDF generation capabilities:
   ```
   pip install reportlab
   ```

## Testing Scripts

There are two scripts provided:

1. **invoke_lambda.py**: Full-featured script that can generate a sample PDF or use your own PDF
2. **invoke_lambda_simple.py**: Simplified script that requires you to provide a PDF file

## Using the Simple Script

This script uploads a PDF file you provide to an S3 bucket and then invokes the Lambda function.

```bash
# Basic usage
python invoke_lambda_simple.py --pdf /path/to/your-file.pdf --bucket your-raw-pdfs-bucket-name

# Using a custom object key
python invoke_lambda_simple.py --pdf /path/to/your-file.pdf --bucket your-raw-pdfs-bucket-name --key custom/path/file.pdf

# Skip uploading and just invoke Lambda on an existing file
python invoke_lambda_simple.py --pdf /path/to/your-file.pdf --bucket your-raw-pdfs-bucket-name --key existing/file.pdf --skip-upload

# Specify a different Lambda function name
python invoke_lambda_simple.py --pdf /path/to/your-file.pdf --bucket your-raw-pdfs-bucket-name --lambda-name custom-lambda-name
```

## Using the Full Script

This script can generate a sample PDF for you if you don't provide one.

```bash
# Generate a sample PDF and upload it
python invoke_lambda.py --bucket your-raw-pdfs-bucket-name

# Use your own PDF
python invoke_lambda.py --pdf /path/to/your-file.pdf --bucket your-raw-pdfs-bucket-name
```

## How It Works

Both scripts:

1. Upload a PDF file to your S3 bucket (unless using --skip-upload)
2. The Lambda function will be automatically triggered by the S3 event notification
3. The script also manually invokes the Lambda with a simulated S3 event
4. The response from the Lambda function is displayed

## Getting the Bucket Name

You can get the bucket name from your Terraform outputs:

```bash
cd terraform/app
terraform output
```

Look for the `raw_pdfs_bucket_name` value.

## Troubleshooting

If you encounter issues:

1. **Access denied errors**: Ensure your AWS CLI is configured with the appropriate permissions
2. **Lambda function not found**: Check if the Lambda function name is correct
3. **PDF upload failures**: Verify the bucket exists and you have permissions to write to it
4. **Lambda timeout**: Check the CloudWatch logs for the Lambda function

## Example Response

A successful Lambda invocation should return something like:

```json
{
  "statusCode": 200,
  "body": {
    "message": "Extracted text from 1 PDF files",
    "results": [
      {
        "source": {
          "bucket": "your-raw-pdfs-bucket-name",
          "file_key": "uploads/1680123456_sample.pdf",
          "size_bytes": 12345,
          "last_modified": "2023-04-01 12:34:56+00:00",
          "content_type": "application/pdf"
        },
        "extracted_text": "Placeholder text for uploads/1680123456_sample.pdf",
        "page_count": 1,
        "status": "success"
      }
    ]
  }
}
```