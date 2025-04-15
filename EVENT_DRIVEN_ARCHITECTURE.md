# Event-Driven Architecture

This document describes the event-driven architecture for document tracking in the EE AI RAG MCP Demo project.

## Overview

The system has been enhanced to use an event-driven architecture for document tracking. This approach provides several benefits:

1. **Decoupling**: Service components are decoupled from the data store, reducing tight dependencies
2. **Scalability**: Services can scale independently and don't need to wait for database operations
3. **Resilience**: Processing continues even if the tracking system experiences issues
4. **Centralization**: Document tracking logic is centralized in one service

## Components

### SNS Topic

A central Amazon SNS topic (`document_indexing`) serves as the messaging backbone of the system. It receives notifications about document processing events and distributes them to subscribers.

### Document Processing Lambdas

Lambda functions that process documents (text_chunker, text_extractor, vector_generator) publish events to the SNS topic instead of directly updating DynamoDB. They publish events for:

- Document processing started
- Document chunk indexed 
- Document indexing completed

### Document Tracking Lambda

A dedicated Lambda function (`document_tracking`) subscribes to the SNS topic and handles all DynamoDB operations. This Lambda:

- Processes incoming SNS messages
- Updates the DynamoDB tracking table
- Ensures data consistency and state management

### Tracking Utils Module

The `tracking_utils.py` module has been modified to:
- Publish events to SNS instead of directly updating DynamoDB
- Maintain backward compatibility with existing code

## Event Types

Three types of events flow through the system:

1. **Document Processing Started**
   - Published when a document begins processing
   - Contains metadata about the document and processing parameters

2. **Document Chunk Indexed**
   - Published when an individual chunk is processed
   - Contains progress information

3. **Document Indexing Completed**
   - Published when all chunks have been processed
   - Marks the document as fully indexed

## Implementation Details

### Terraform Configuration

A new Terraform module (`document_tracking.tf`) defines:
- The Document Tracking Lambda
- Required IAM permissions
- SNS subscription
- Lambda layer for dependencies

### Testing

Comprehensive unit tests validate the behavior of:
- SNS message parsing
- Error handling
- DynamoDB update logic

## Migration Strategy

This architecture change is backward compatible. If issues occur with the new SNS-based approach, the system can revert to direct DynamoDB updates without affecting API users or requiring data migration.