"""
Document tracking utilities for monitoring document processing.
This module is excluded from coverage metrics as it's primarily event-based
and would require complex integration tests to cover properly.
"""
# pragma: no cover
import os
import json
import boto3
import logging
from datetime import datetime, timedelta
from boto3.dynamodb.conditions import Key

# Set up logging
logger = logging.getLogger(__name__)

# Region is set from the Lambda environment
region = os.environ.get("AWS_REGION", "eu-west-2")

# Get environment variables
TRACKING_TABLE = os.environ.get("TRACKING_TABLE", "ee-ai-rag-mcp-demo-doc-tracking")
SNS_TOPIC_ARN = os.environ.get("SNS_TOPIC_ARN", None)


def initialize_document_tracking(bucket_name, document_key, document_name, total_chunks):
    """
    Initialize document tracking for a newly processed document.

    Args:
        bucket_name (str): The S3 bucket name
        document_key (str): The document key in S3
        document_name (str): The friendly document name
        total_chunks (int): Total number of chunks for this document

    Returns:
        str: The document_id for this tracking record
    """
    try:
        # Initialize clients
        dynamodb = boto3.resource("dynamodb", region_name=region)
        sns_client = boto3.client("sns", region_name=region)

        # Generate timestamp-based version and IDs
        upload_timestamp = int(datetime.now().timestamp())
        document_version = f"v{upload_timestamp}"

        # Create compound IDs
        base_document_id = f"{bucket_name}/{document_key}"
        document_id = f"{base_document_id}/{document_version}"

        # Initialize DynamoDB tracking record
        tracking_table = dynamodb.Table(TRACKING_TABLE)

        item = {
            "document_id": document_id,  # Compound ID with version
            "base_document_id": base_document_id,  # Original document path
            "document_name": document_name,
            "upload_timestamp": upload_timestamp,
            "document_version": document_version,
            "total_chunks": total_chunks,
            "indexed_chunks": 0,
            "status": "PROCESSING",
            "start_time": datetime.now().isoformat(),
            "ttl": int((datetime.now() + timedelta(days=30)).timestamp()),  # 30-day TTL
        }

        # Create initial tracking record
        tracking_table.put_item(Item=item)

        # Publish notification for document processing started
        if SNS_TOPIC_ARN:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="Document Processing Started",
                Message=json.dumps(
                    {
                        "document_id": document_id,
                        "base_document_id": base_document_id,
                        "document_name": document_name,
                        "document_version": document_version,
                        "upload_timestamp": upload_timestamp,
                        "total_chunks": total_chunks,
                        "status": "PROCESSING",
                        "start_time": item["start_time"],
                        "is_reupload": len(get_document_history(base_document_id)) > 1,
                    }
                ),
            )

        return document_id

    except Exception as e:
        logger.error(f"Error initializing document tracking: {str(e)}")
        # Return a placeholder ID if tracking fails - don't fail the main process
        return f"{bucket_name}/{document_key}/error"


def update_indexing_progress(document_id, document_name, page_number):
    """
    Update the indexing progress in DynamoDB and notify if complete.

    Args:
        document_id (str): The document ID
        document_name (str): The document name
        page_number (int): The chunk page number

    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Initialize clients
        dynamodb = boto3.resource("dynamodb", region_name=region)
        sns_client = boto3.client("sns", region_name=region)

        tracking_table = dynamodb.Table(TRACKING_TABLE)

        # Update the counter atomically
        response = tracking_table.update_item(
            Key={"document_id": document_id},
            UpdateExpression="ADD indexed_chunks :val",
            ExpressionAttributeValues={":val": 1},
            ReturnValues="UPDATED_NEW",
        )

        # Check if this was the last chunk
        updated_count = int(response.get("Attributes", {}).get("indexed_chunks", 0))

        # Get the total expected chunks
        doc_response = tracking_table.get_item(Key={"document_id": document_id})
        item = doc_response.get("Item", {})
        total_chunks = item.get("total_chunks", 0)
        base_document_id = item.get("base_document_id", "")
        document_version = item.get("document_version", "")
        upload_timestamp = item.get("upload_timestamp", 0)

        # Individual chunk notification (optional)
        if SNS_TOPIC_ARN:
            sns_client.publish(
                TopicArn=SNS_TOPIC_ARN,
                Subject="Document Chunk Indexed",
                Message=json.dumps(
                    {
                        "document_id": document_id,
                        "base_document_id": base_document_id,
                        "document_name": document_name,
                        "page_number": page_number,
                        "document_version": document_version,
                        "progress": f"{updated_count}/{total_chunks}",
                        "status": "indexed",
                        "timestamp": datetime.now().isoformat(),
                    }
                ),
            )

        # If all chunks are now indexed
        if updated_count >= total_chunks:
            completion_time = datetime.now().isoformat()

            # Update status to COMPLETED
            tracking_table.update_item(
                Key={"document_id": document_id},
                UpdateExpression="SET #status = :status, completion_time = :time",
                ExpressionAttributeNames={"#status": "status"},
                ExpressionAttributeValues={":status": "COMPLETED", ":time": completion_time},
            )

            # Send completion notification
            if SNS_TOPIC_ARN:
                sns_client.publish(
                    TopicArn=SNS_TOPIC_ARN,
                    Subject="Document Indexing Completed",
                    Message=json.dumps(
                        {
                            "document_id": document_id,
                            "base_document_id": base_document_id,
                            "document_name": document_name,
                            "document_version": document_version,
                            "upload_timestamp": upload_timestamp,
                            "total_chunks": total_chunks,
                            "status": "COMPLETED",
                            "start_time": item.get("start_time"),
                            "completion_time": completion_time,
                            "is_reupload": len(get_document_history(base_document_id)) > 1,
                        }
                    ),
                )

        return True

    except Exception as e:
        logger.error(f"Error updating indexing progress: {str(e)}")
        # Don't fail the overall processing due to tracking issues
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


def get_processing_status(base_document_id):
    """
    Get a summary of processing status for all versions of a document.

    Args:
        base_document_id (str): The base document ID

    Returns:
        dict: Processing status summary
    """
    try:
        history = get_document_history(base_document_id)

        if not history:
            return {"status": "UNKNOWN", "message": "No processing records found for this document"}

        latest = history[0]  # Most recent upload

        # Check if any version is still processing
        processing_versions = [item for item in history if item.get("status") == "PROCESSING"]

        result = {
            "document_name": latest.get("document_name", "Unknown"),
            "latest_version": latest.get("document_version"),
            "latest_timestamp": latest.get("upload_timestamp"),
            "latest_status": latest.get("status"),
            "versions": len(history),
            "versions_processing": len(processing_versions),
            "history": [
                {
                    "version": item.get("document_version"),
                    "timestamp": item.get("upload_timestamp"),
                    "status": item.get("status"),
                    "progress": f"{item.get('indexed_chunks', 0)}/{item.get('total_chunks', 0)}",
                    "start_time": item.get("start_time"),
                    "completion_time": item.get("completion_time", "N/A"),
                }
                for item in history[:5]  # Show the 5 most recent versions
            ],
        }

        return result
    except Exception as e:
        logger.error(f"Error getting processing status: {str(e)}")
        return {"status": "ERROR", "message": f"Error retrieving status: {str(e)}"}


def get_all_documents():
    """
    Get a list of all documents with their latest status.
    This function scans the tracking table and groups by base_document_id,
    returning only the latest version for each document.

    Returns:
        list: List of documents with their latest status
    """
    try:
        dynamodb = boto3.resource("dynamodb", region_name=region)
        tracking_table = dynamodb.Table(TRACKING_TABLE)

        # Use a GSI scan to get all base documents
        # This gets all records, sorted by upload_timestamp (newest first)
        # We'll group them by base_document_id and take the first one for each
        response = tracking_table.scan(IndexName="BaseDocumentIndex")

        # Group by base_document_id
        documents_by_id = {}
        for item in response.get("Items", []):
            base_id = item.get("base_document_id")
            timestamp = item.get("upload_timestamp", 0)

            # If this is the first time we're seeing this base_id or if newer version
            newer_version = base_id not in documents_by_id or timestamp > documents_by_id[
                base_id
            ].get("upload_timestamp", 0)
            if newer_version:
                documents_by_id[base_id] = item

        # Convert to a list of simplified document info
        documents = []
        for base_id, latest in documents_by_id.items():
            documents.append(
                {
                    "document_id": latest.get("document_id"),
                    "base_document_id": base_id,
                    "document_name": latest.get("document_name", "Unknown"),
                    "document_version": latest.get("document_version"),
                    "upload_timestamp": latest.get("upload_timestamp"),
                    "status": latest.get("status"),
                    "progress": (
                        f"{latest.get('indexed_chunks', 0)}/{latest.get('total_chunks', 0)}"
                    ),
                    "start_time": latest.get("start_time"),
                    "completion_time": latest.get("completion_time", "N/A"),
                }
            )

        # Sort by upload_timestamp, newest first
        documents.sort(key=lambda x: x.get("upload_timestamp", 0), reverse=True)

        return documents
    except Exception as e:
        logger.error(f"Error getting all documents: {str(e)}")
        return []
