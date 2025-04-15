# Event-Driven Architecture for Document Tracking

This document explains the new event-driven architecture implemented for document tracking.

## Overview

The document processing pipeline has been refactored to follow a more decoupled, event-driven approach:

1. Processing lambdas (`text_chunker`, `vector_generator`) now only publish events to SNS topics
2. A dedicated `document_tracking` lambda subscribes to these events and handles DynamoDB updates
3. Existing API endpoints continue to work unchanged, reading from the same DynamoDB table

## Benefits

This architectural change provides several advantages:

- **Better separation of concerns**: Processing lambdas focus solely on their data processing tasks
- **Improved scalability**: SNS provides fan-out capabilities if more subscribers are added later
- **Enhanced reliability**: Document tracking failures don't impact the main processing pipeline
- **Easier monitoring**: SNS metrics provide visibility into event flow
- **Simplified maintenance**: Changes to document tracking logic are isolated to a single lambda

## Implementation

### Components

1. **SNS Topic**: `ee-ai-rag-mcp-demo-document-indexing`
   - Receives all document tracking events

2. **Document Tracking Lambda**: `ee-ai-rag-mcp-demo-document-tracking`
   - Subscribes to the SNS topic
   - Processes three types of events:
     - `Document Processing Started`: Initializes tracking records
     - `Document Chunk Indexed`: Updates progress counters
     - `Document Indexing Completed`: Marks documents as complete

3. **Modified Tracking Utils**: `tracking_utils.py`
   - No longer updates DynamoDB directly
   - Only publishes events to SNS

### Event Flow

1. Document uploaded → `text_chunker` lambda:
   - Processes document into chunks
   - Publishes `Document Processing Started` event

2. Chunks processed → `vector_generator` lambda:
   - Generates vector embeddings
   - Publishes `Document Chunk Indexed` event for each chunk
   - Publishes `Document Indexing Completed` event when all chunks are done

3. Events → `document_tracking` lambda:
   - Subscribes to all events
   - Updates DynamoDB tracking table based on event type

## Future Enhancements

Possible future improvements to this architecture:

1. Add DLQ (Dead Letter Queue) for failed SNS message processing
2. Implement more granular event types for better monitoring
3. Add CloudWatch alarms for tracking failures
4. Create dashboard for document processing visualization