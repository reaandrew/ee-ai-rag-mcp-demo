import json
import boto3
import logging
import os
import decimal
from datetime import datetime, timedelta

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Region is set from the Lambda environment
region = os.environ.get("AWS_REGION", "eu-west-2")

# Get environment variables
TRACKING_TABLE = os.environ.get("TRACKING_TABLE", "ee-ai-rag-mcp-demo-doc-tracking")

# Initialize DynamoDB client
dynamodb = boto3.resource("dynamodb", region_name=region)
tracking_table = dynamodb.Table(TRACKING_TABLE)


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


def initialize_document_tracking(message_data):
    """
    Initialize document tracking for a newly processed document.

    Args:
        message_data (dict): The SNS message data

    Returns:
        bool: Success status
    """
    try:
        # Extract relevant data from the SNS message
        document_id = message_data.get("document_id")
        base_document_id = message_data.get("base_document_id")
        document_name = message_data.get("document_name")
        document_version = message_data.get("document_version")
        upload_timestamp = message_data.get("upload_timestamp")
        total_chunks = message_data.get("total_chunks")
        start_time = message_data.get("start_time")
        is_reupload = message_data.get("is_reupload", False)

        logger.info(f"Initializing document tracking for {document_id}")

        # Check if there are any existing versions of this document in processing state
        if is_reupload:
            existing_docs = get_document_history(base_document_id)
            for doc in existing_docs:
                if doc.get("status") == "PROCESSING" and doc.get("document_id") != document_id:
                    # Clean up processing records for the same document
                    logger.info(
                        f"Found existing processing record for {base_document_id}. Cleaning up."
                    )
                    tracking_table.update_item(
                        Key={"document_id": doc.get("document_id")},
                        UpdateExpression="SET #status = :status",
                        ExpressionAttributeNames={"#status": "status"},
                        ExpressionAttributeValues={":status": "CANCELLED"},
                    )

        # Initialize DynamoDB tracking record
        item = {
            "document_id": document_id,
            "base_document_id": base_document_id,
            "document_name": document_name,
            "upload_timestamp": upload_timestamp,
            "document_version": document_version,
            "total_chunks": total_chunks,
            "indexed_chunks": 0,
            "status": "PROCESSING",
            "start_time": start_time or datetime.now().isoformat(),
            "ttl": int((datetime.now() + timedelta(days=30)).timestamp()),  # 30-day TTL
        }

        # Create initial tracking record
        tracking_table.put_item(Item=item)

        return True
    except Exception as e:
        logger.error(f"Error initializing document tracking: {str(e)}")
        return False


def update_indexing_progress(message_data):
    """
    Update the indexing progress in DynamoDB.

    Args:
        message_data (dict): The SNS message data

    Returns:
        bool: Success status
    """
    try:
        # Extract relevant data from the message
        document_id = message_data.get("document_id")
        progress = message_data.get("progress")

        if not document_id:
            logger.error("No document_id provided in message data")
            return False

        # First get the current document to check total chunks and current count
        doc_response = tracking_table.get_item(Key={"document_id": document_id})
        item = doc_response.get("Item", {})
        total_chunks = item.get("total_chunks", 0)
        current_chunks = item.get("indexed_chunks", 0)

        if "progress" in message_data:
            # If progress is provided, parse it
            try:
                parts = progress.split("/")
                updated_count = int(parts[0])
                # Only update if the count is higher than what we have
                if updated_count > current_chunks:
                    tracking_table.update_item(
                        Key={"document_id": document_id},
                        UpdateExpression="SET indexed_chunks = :val",
                        ExpressionAttributeValues={":val": updated_count},
                        ConditionExpression="indexed_chunks < :val",
                    )
                    logger.info(
                        f"Updated progress for {document_id} to " f"{updated_count}/{total_chunks}"
                    )
            except Exception as e:
                logger.error(f"Error parsing progress '{progress}': {str(e)}")
        else:
            # If no progress provided, increment the counter
            try:
                response = tracking_table.update_item(
                    Key={"document_id": document_id},
                    UpdateExpression="ADD indexed_chunks :val",
                    ConditionExpression="indexed_chunks < :total",
                    ExpressionAttributeValues={":val": 1, ":total": total_chunks},
                    ReturnValues="UPDATED_NEW",
                )

                updated_count = int(response.get("Attributes", {}).get("indexed_chunks", 0))
                logger.info(
                    f"Incremented progress for {document_id} to " f"{updated_count}/{total_chunks}"
                )
            except tracking_table.meta.client.exceptions.ConditionalCheckFailedException:
                logger.warning(
                    f"Concurrent update prevented excess increment for {document_id}. "
                    f"Current chunks {current_chunks}/{total_chunks}."
                )

        return True
    except Exception as e:
        logger.error(f"Error updating indexing progress: {str(e)}")
        return False


def complete_document_indexing(message_data):
    """
    Mark document indexing as complete.

    Args:
        message_data (dict): The SNS message data

    Returns:
        bool: Success status
    """
    try:
        # Extract relevant data from the message
        document_id = message_data.get("document_id")
        total_chunks = message_data.get("total_chunks")
        completion_time = message_data.get("completion_time", datetime.now().isoformat())

        if not document_id:
            logger.error("No document_id provided in message data")
            return False

        # Update status to COMPLETED and ensure indexed_chunks = total_chunks
        tracking_table.update_item(
            Key={"document_id": document_id},
            UpdateExpression=(
                "SET #status = :status, completion_time = :time, indexed_chunks = :total"
            ),
            ExpressionAttributeNames={"#status": "status"},
            ExpressionAttributeValues={
                ":status": "COMPLETED",
                ":time": completion_time,
                ":total": total_chunks,
            },
        )

        logger.info(f"Marked document {document_id} as COMPLETED")
        return True
    except Exception as e:
        logger.error(f"Error completing document indexing: {str(e)}")
        return False


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
        response = tracking_table.query(
            IndexName="BaseDocumentIndex",
            KeyConditionExpression=boto3.dynamodb.conditions.Key("base_document_id").eq(
                base_document_id
            ),
            ScanIndexForward=False,  # Newest first
        )

        return response.get("Items", [])
    except Exception as e:
        logger.error(f"Error getting document history: {str(e)}")
        return []


def lambda_handler(event, context):
    """
    Lambda handler for processing SNS document tracking events.

    Args:
        event (dict): The Lambda event
        context (LambdaContext): The Lambda context

    Returns:
        dict: Response data
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        processed_count = 0
        success_count = 0

        # Process each record (SNS message)
        for record in event.get("Records", []):
            processed_count += 1

            # Parse the SNS message
            sns_message = record.get("Sns", {})
            message_text = sns_message.get("Message", "{}")
            subject = sns_message.get("Subject", "")

            try:
                message_data = json.loads(message_text)
            except json.JSONDecodeError:
                logger.error(f"Failed to parse SNS message as JSON: {message_text}")
                continue

            # Route to the appropriate handler based on the message subject
            result = False
            if subject == "Document Processing Started":
                result = initialize_document_tracking(message_data)
            elif subject == "Document Chunk Indexed":
                result = update_indexing_progress(message_data)
            elif subject == "Document Indexing Completed":
                result = complete_document_indexing(message_data)
            else:
                logger.warning(f"Unknown message subject: {subject}")

            if result:
                success_count += 1

        return {
            "statusCode": 200,
            "body": {
                "message": f"Processed {success_count}/{processed_count} document tracking events",
            },
        }

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {
            "statusCode": 500,
            "body": {"message": f"Error processing SNS events: {str(e)}"},
        }
