"""
Document tracking Lambda function for processing SNS events.
This Lambda subscribes to SNS topics and updates DynamoDB with tracking information.
"""
import json
import logging
import os
import boto3
import decimal
from datetime import datetime
from boto3.dynamodb.conditions import Key


# Helper class to convert Decimal objects to int/float for JSON serialization
class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, decimal.Decimal):
            # Convert decimals to integers or floats
            if o % 1 == 0:
                return int(o)
            else:
                return float(o)
        return super(DecimalEncoder, self).default(o)


# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Region is set from the Lambda environment
region = os.environ.get("AWS_REGION", "eu-west-2")

# Get environment variables
TRACKING_TABLE = os.environ.get("TRACKING_TABLE", "ee-ai-rag-mcp-demo-doc-tracking")

# Constants
ERROR_MISSING_REQUIRED_FIELDS = "Missing required fields in message data"


def get_document_history(base_document_id):
    """
    Get the processing history for a document across multiple uploads.
    Returns the list of processing records sorted by timestamp (newest first).

    Args:
        base_document_id (str): The base document ID

    Returns:
        list: Processing records sorted by timestamp
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        tracking_table = dynamodb.Table(TRACKING_TABLE)

        response = tracking_table.query(
            IndexName="BaseDocumentIndex",
            KeyConditionExpression=Key("base_document_id").eq(base_document_id),
            ScanIndexForward=False,  # Newest first
        )

        return response.get("Items", [])
    except Exception as e:
        logger.error(f"Error getting document history: {str(e)}")
        return []


def complete_document_indexing(message_data):
    """
    Mark document indexing as completed.

    Args:
        message_data (dict): Data from the SNS message

    Returns:
        dict: Result of the operation
    """
    try:
        # Extract data from the message
        document_id = message_data.get("document_id")
        total_chunks = message_data.get("total_chunks")
        completion_time = message_data.get("completion_time", datetime.now().isoformat())

        # Validate required fields
        if not all([document_id, total_chunks]):
            return {"status": "error", "message": ERROR_MISSING_REQUIRED_FIELDS}

        logger.info(f"Completing indexing for document: {document_id}")

        # Update DynamoDB record to mark document as COMPLETED
        dynamodb = boto3.resource("dynamodb", region_name=region)
        tracking_table = dynamodb.Table(TRACKING_TABLE)
        try:
            # Only update if status isn't already COMPLETED (avoid race conditions)
            update_result = tracking_table.update_item(
                Key={"document_id": document_id},
                UpdateExpression=(
                    "SET #status = :status, "
                    "completion_time = :completion_time, "
                    "indexed_chunks = :total_chunks"
                ),
                ConditionExpression="#status <> :completed_status",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={
                    ":status": "COMPLETED",
                    ":completion_time": completion_time,
                    ":completed_status": "COMPLETED",
                    ":total_chunks": total_chunks,  # Ensure indexed_chunks equals total_chunks
                },
                ReturnValues="UPDATED_NEW",
            )
            logger.info(f"Marked document {document_id} as COMPLETED via explicit message")
        except Exception as e:
            if "ConditionalCheckFailedException" in str(e):
                logger.info(f"Document {document_id} already marked as COMPLETED")
                # Get the current status for logging
                item_response = tracking_table.get_item(Key={"document_id": document_id})
                current_item = item_response.get("Item", {})
                logger.info(f"Current state: {json.dumps(current_item, cls=DecimalEncoder)}")
                update_result = {"Attributes": current_item}
            else:
                logger.warning(f"Error marking document {document_id} as COMPLETED: {str(e)}")
                raise
        logger.info(f"DynamoDB update result: {json.dumps(update_result, cls=DecimalEncoder)}")

        return {
            "status": "success",
            "document_id": document_id,
            "message": f"Document indexing completed for {document_id}",
        }

    except Exception as e:
        logger.error(f"Error completing document indexing: {str(e)}")
        return {"status": "error", "message": f"Error completing document indexing: {str(e)}"}


def update_indexing_progress(message_data):
    """
    Update the indexing progress for a document chunk.

    Args:
        message_data (dict): Data from the SNS message

    Returns:
        dict: Result of the operation
    """
    try:
        # Extract data from the message
        document_id = message_data.get("document_id")
        page_number = message_data.get("page_number")
        # We don't use the progress value from the message as we calculate it ourselves
        message_data.get("progress", "0/0")  # Accessing but not storing the value

        # Extract document name for debugging problematic documents
        document_name = message_data.get("document_name", "Unknown")

        # Enhanced logging for problematic documents
        problematic_docs = ["internet_usage_policy.txt", "Remote_Access_Policy.txt"]
        is_problematic = any(doc in document_name for doc in problematic_docs)

        # Validate required fields
        if not all([document_id, page_number]):
            return {"status": "error", "message": ERROR_MISSING_REQUIRED_FIELDS}

        logger.info(f"Updating: doc={document_id}, name={document_name}, page={page_number}")

        # Update DynamoDB record with progress
        dynamodb = boto3.resource("dynamodb", region_name=region)
        tracking_table = dynamodb.Table(TRACKING_TABLE)

        # First get the current item to check total_chunks (we need this for progress reporting)
        item_response = tracking_table.get_item(Key={"document_id": document_id})
        current_item = item_response.get("Item", {})
        total_chunks = current_item.get("total_chunks", 0)
        indexed_chunks = current_item.get("indexed_chunks", 0)

        if is_problematic:
            logger.info(
                f"PROBLEMATIC: {document_name} - indexed={indexed_chunks}, total={total_chunks}"
            )

        # Use DynamoDB's atomic counter increment instead of read-then-write pattern
        # This avoids race conditions when multiple chunks are processed simultaneously
        update_result = tracking_table.update_item(
            Key={"document_id": document_id},
            UpdateExpression="ADD indexed_chunks :inc",
            ExpressionAttributeValues={
                ":inc": 1,  # Increment by 1 atomically
            },
            ReturnValues="UPDATED_NEW",
        )

        # Get the new incremented value from the update result
        new_indexed_chunks = update_result["Attributes"].get("indexed_chunks", 0)
        progress_str = f"{new_indexed_chunks}/{total_chunks}"

        # Update the progress_info field with the actual incremented value
        tracking_table.update_item(
            Key={"document_id": document_id},
            UpdateExpression="SET progress_info = :progress",
            ExpressionAttributeValues={
                ":progress": progress_str,
            },
        )

        # Check if we've completed all chunks and should mark as completed
        if total_chunks > 0 and new_indexed_chunks >= total_chunks:
            logger.info(f"All chunks processed for {document_name}, setting to COMPLETED")
            completion_time = datetime.now().isoformat()
            try:
                # Only update if status isn't already COMPLETED (avoid race conditions)
                tracking_table.update_item(
                    Key={"document_id": document_id},
                    UpdateExpression="SET #status = :status, completion_time = :completion_time",
                    ConditionExpression="#status <> :completed_status",
                    ExpressionAttributeNames={"#status": "status"},
                    ExpressionAttributeValues={
                        ":status": "COMPLETED",
                        ":completion_time": completion_time,
                        ":completed_status": "COMPLETED",
                    },
                )
                logger.info(f"Successfully marked {document_name} as COMPLETED")
            except Exception as e:
                # If condition fails or other error, log but don't fail
                if "ConditionalCheckFailedException" in str(e):
                    logger.info(f"Document {document_name} already marked as COMPLETED")
                else:
                    logger.warning(f"Error marking document {document_name} as COMPLETED: {str(e)}")
        elif is_problematic:
            # Extra logging for problematic documents
            logger.info(
                (
                    f"PROGRESS CHECK: {document_name} - "
                    f"indexed={new_indexed_chunks}, total={total_chunks}, "
                    f"should_complete={(total_chunks > 0 and new_indexed_chunks >= total_chunks)}"
                )
            )
        logger.info(f"DynamoDB update result: {json.dumps(update_result, cls=DecimalEncoder)}")

        return {
            "status": "success",
            "document_id": document_id,
            "document_name": document_name,
            "progress": progress_str,
            "message": f"Document indexing progress updated for {document_id} ({document_name})",
        }

    except Exception as e:
        logger.error(f"Error updating indexing progress: {str(e)}")
        return {"status": "error", "message": f"Error updating indexing progress: {str(e)}"}


def initialize_document_tracking(message_data):
    """
    Initialize document tracking for a newly processed document.

    Args:
        message_data (dict): Data from the SNS message

    Returns:
        dict: Result of the operation
    """
    try:
        # Extract data from the message
        document_id = message_data.get("document_id")
        base_document_id = message_data.get("base_document_id")
        document_name = message_data.get("document_name", "Unknown")
        total_chunks = message_data.get("total_chunks")
        document_version = message_data.get("document_version", "v1")

        # Calculate upload timestamp if not provided
        upload_timestamp = message_data.get("upload_timestamp", int(datetime.now().timestamp()))
        start_time = message_data.get("start_time", datetime.now().isoformat())

        # Validate required fields
        if not all([document_id, base_document_id, total_chunks]):
            return {"status": "error", "message": ERROR_MISSING_REQUIRED_FIELDS}

        logger.info(f"Initializing tracking for document: {document_id}, chunks: {total_chunks}")

        # Create new record in DynamoDB
        dynamodb = boto3.resource("dynamodb", region_name=region)
        tracking_table = dynamodb.Table(TRACKING_TABLE)
        # Prepare item for DynamoDB
        tracking_item = {
            "document_id": document_id,
            "base_document_id": base_document_id,
            "document_name": document_name,
            "document_version": document_version,
            "upload_timestamp": upload_timestamp,
            "total_chunks": total_chunks,
            "indexed_chunks": 0,
            "status": "PROCESSING",
            "start_time": start_time,
        }
        # Write to DynamoDB
        put_result = tracking_table.put_item(Item=tracking_item)
        logger.info(f"DynamoDB put_item result: {json.dumps(put_result, cls=DecimalEncoder)}")

        return {
            "status": "success",
            "document_id": document_id,
            "message": f"Document tracking initialized for {document_id}",
        }

    except Exception as e:
        logger.error(f"Error initializing document tracking: {str(e)}")
        return {"status": "error", "message": f"Error initializing document tracking: {str(e)}"}


def lambda_handler(event, context):
    """
    Lambda handler for processing SNS events.

    Args:
        event (dict): Event data from SNS
        context (LambdaContext): Lambda context

    Returns:
        dict: Response with processing results
    """
    logger.info(f"Received event: {json.dumps(event)}")

    processed_count = 0
    results = []

    try:
        # Check if this is a valid SNS event
        if "Records" not in event:
            raise ValueError("Invalid event structure: 'Records' field is missing")

        # Process each record (SNS message)
        for record in event.get("Records", []):
            processed_count += 1

            # Parse the SNS message
            sns_message = record.get("Sns", {})
            message_text = sns_message.get("Message", "{}")
            subject = sns_message.get("Subject", "")

            try:
                message_data = json.loads(message_text)

                # Route to the appropriate handler based on the message subject
                if subject == "Document Processing Started":
                    result = initialize_document_tracking(message_data)
                elif subject == "Document Chunk Indexed":
                    result = update_indexing_progress(message_data)
                elif subject == "Document Indexing Completed":
                    result = complete_document_indexing(message_data)
                else:
                    # For unknown subjects, just log receipt
                    logger.info(f"Received unknown message subject: {subject}")
                    result = {
                        "status": "success",
                        "message": f"Received message with unknown subject: {subject}",
                    }

                results.append(result)

            except json.JSONDecodeError:
                logger.error(f"Invalid JSON in SNS message: {message_text}")
                results.append({"status": "error", "message": "Invalid JSON in SNS message"})

        return {
            "statusCode": 200,
            "body": {"message": f"Processed {processed_count} SNS events", "results": results},
        }
    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": {"message": f"Error processing SNS events: {str(e)}"}}
