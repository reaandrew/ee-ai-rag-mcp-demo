# Document Tracking Lambda

This Lambda function subscribes to SNS notifications from the document processing pipeline
and updates DynamoDB with document status information.

## Purpose

This Lambda implements a more decoupled, event-driven architecture by:

1. Subscribing to SNS topics instead of having processing lambdas write directly to DynamoDB
2. Processing different types of document events:
   - Document Processing Started
   - Document Chunk Indexed 
   - Document Indexing Completed

## Environment Variables

- `TRACKING_TABLE`: The DynamoDB table name for document tracking (default: "ee-ai-rag-mcp-demo-doc-tracking")
- `AWS_REGION`: The AWS region (provided by Lambda runtime)

## Input

This Lambda processes SNS messages with the following subjects:

- `Document Processing Started`: Initialize tracking for a new document
- `Document Chunk Indexed`: Update indexing progress for a document
- `Document Indexing Completed`: Mark document processing as complete

## Output

The Lambda returns a response with the count of processed events.