# Document Tracking Lambda

This Lambda function subscribes to SNS topics and updates DynamoDB with document tracking information.

## Purpose

The Document Tracking Lambda serves as a centralized service for maintaining document processing state in DynamoDB. It works with the event-driven architecture by:

1. Receiving SNS notifications about document processing events
2. Updating the DynamoDB tracking table based on these events
3. Ensuring data consistency and proper state management

## Event Types

The Lambda processes three types of SNS events:

1. **Document Processing Started**: Initializes tracking for a new document
2. **Document Chunk Indexed**: Updates progress as chunks are processed
3. **Document Indexing Completed**: Marks document processing as complete

## Architecture

This Lambda is part of an event-driven architecture where:

- Document processing lambdas (text_chunker, text_extractor, vector_generator) publish events to SNS
- The document_tracking Lambda subscribes to these events
- DynamoDB is updated by this Lambda rather than directly by processing lambdas
- This centralization improves scalability and reduces tight coupling