import json
import boto3
import logging
import os
from urllib.parse import unquote_plus
from langchain_text_splitters import RecursiveCharacterTextSplitter

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize S3 client with default region
default_region = "eu-west-2"  # Match your region in Terraform config or AWS
s3_client = boto3.client("s3", region_name=default_region)

# Get environment variables
CHUNKED_TEXT_BUCKET = os.environ.get("CHUNKED_TEXT_BUCKET", "ee-ai-rag-mcp-demo-chunked-text")
CHUNKED_TEXT_PREFIX = os.environ.get("CHUNKED_TEXT_PREFIX", "ee-ai-rag-mcp-demo")
CHUNK_SIZE = int(os.environ.get("CHUNK_SIZE", "1000"))
CHUNK_OVERLAP = int(os.environ.get("CHUNK_OVERLAP", "200"))


def parse_page_info(text):
    """
    Parse text with page delimiters to extract page numbers, build a 'cleaned' text,
    and record where each new page begins in that cleaned text.

    Returns:
        (cleaned_text, page_map) where page_map is a dict of {offset_in_cleaned_text: page_number}.
    """
    import re

    page_pattern = re.compile(r"\n--- PAGE (\d+) ---\n")
    page_markers = list(page_pattern.finditer(text))

    if not page_markers:
        # No page markers found; treat entire text as page 1
        return text, {0: 1}

    # Create a mapping from character position to page number
    page_map = {0: 1}  # Start with page 1 at offset 0
    cleaned_text = ""

    for i, marker in enumerate(page_markers):
        page_num = int(marker.group(1))

        # Start position after the marker
        start_pos = marker.end()

        # End position (next marker or end of text)
        if i < len(page_markers) - 1:
            end_pos = page_markers[i + 1].start()
        else:
            end_pos = len(text)

        # Extract the text for this page
        page_text = text[start_pos:end_pos]

        # Append the page's text (excluding the marker) into cleaned_text
        cleaned_text += page_text

        # Record the end of this page's text as the start of the next page
        if i < len(page_markers) - 1:
            page_map[len(cleaned_text)] = page_num + 1

    return cleaned_text, page_map


def build_page_ranges(cleaned_text, page_map):
    """
    Convert the page_map into a list of (start_offset, end_offset, page_number).
    Each tuple describes the exact range of a page in the cleaned text.
    """
    page_ranges = []
    positions = sorted(page_map.keys())
    for i in range(len(positions)):
        start_offset = positions[i]
        page_num = page_map[start_offset]
        if i < len(positions) - 1:
            end_offset = positions[i + 1]
        else:
            end_offset = len(cleaned_text)
        page_ranges.append((start_offset, end_offset, page_num))
    return page_ranges


def find_page_for_chunk(chunk_start, chunk_end, page_ranges):
    """
    Given a chunk's [chunk_start, chunk_end) offsets in the cleaned text,
    return a list of page numbers that overlap with that chunk range.
    Prioritize the page where chunk_start lies to avoid off-by-one errors.
    """
    chunk_pages = []
    for page_start, page_end, page_num in page_ranges:
        # Skip if page ends before chunk starts
        if page_end <= chunk_start:
            continue
        # Stop if page starts after chunk ends
        if page_start >= chunk_end:
            break
        # Include page if chunk starts within page or overlaps
        if page_start <= chunk_start < page_end or (
            chunk_start < page_start and chunk_end > page_start
        ):
            chunk_pages.append(page_num)
    # Deduplicate while preserving order
    seen = set()
    chunk_pages = [p for p in chunk_pages if not (p in seen or seen.add(p))]
    return chunk_pages if chunk_pages else [1]


def chunk_text(text, metadata=None):
    """
    Split text into chunks using RecursiveCharacterTextSplitter.
    Store page numbers by checking each chunk's text range against the page_ranges.
    """
    logger.info(f"Chunking text of length {len(text)} characters")

    # 1) Parse out page info
    cleaned_text, page_map = parse_page_info(text)
    page_ranges = build_page_ranges(cleaned_text, page_map)

    # 2) Create a text splitter with the specified config
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,
        separators=["\n\n", "\n", " ", ""],
    )

    # 3) Split into chunks
    chunks = text_splitter.split_text(cleaned_text)
    logger.info(f"Created {len(chunks)} chunks")

    result = []
    pos = 0  # Keep track of where we are in cleaned_text

    for i, chunk in enumerate(chunks):
        chunk_start = pos
        chunk_end = pos + len(chunk)

        # Determine which pages this chunk spans
        chunk_pages = find_page_for_chunk(chunk_start, chunk_end, page_ranges)

        # The first page in chunk_pages is start_page; last is end_page
        start_page = chunk_pages[0]
        end_page = chunk_pages[-1]

        # Modify page_number to represent the full range if applicable
        if start_page == end_page:
            page_number_display = str(start_page)
        else:
            page_number_display = f"{start_page}-{end_page}"

        chunk_info = {
            "chunk_id": i,
            "total_chunks": len(chunks),
            "text": chunk,
            "chunk_size": len(chunk),
            "pages": chunk_pages,
            "page_number": page_number_display,  # Now shows range if applicable
            "document_name": metadata.get("filename", "") if metadata else "",
            "start_page": start_page,
            "end_page": end_page,
        }

        # For next iteration, account for overlap
        if i < len(chunks) - 1:
            pos = chunk_end - CHUNK_OVERLAP
        else:
            pos = chunk_end

        # Optionally attach entire metadata
        if metadata:
            meta_copy = metadata.copy()
            meta_copy["pages"] = chunk_pages
            meta_copy["page_number"] = page_number_display
            meta_copy["start_page"] = start_page
            meta_copy["end_page"] = end_page
            meta_copy["document_name"] = metadata.get("filename", "")
            chunk_info["metadata"] = meta_copy

        result.append(chunk_info)

    return result


def process_text_file(bucket_name, file_key):
    """
    Process a text file from S3, chunk it, and save chunks to the destination bucket.
    """
    logger.info(f"Processing text file: {file_key} in bucket {bucket_name}")

    try:
        # Get the object metadata
        metadata = s3_client.head_object(Bucket=bucket_name, Key=file_key)

        # Get the text content
        response = s3_client.get_object(Bucket=bucket_name, Key=file_key)
        text_content = response["Body"].read().decode("utf-8")

        # Extract filename without extension
        filename = os.path.basename(file_key)
        filename_without_ext = os.path.splitext(filename)[0]

        # Prepare metadata for chunks
        file_metadata = {
            "source_bucket": bucket_name,
            "source_key": file_key,
            "filename": filename,
            "content_type": metadata.get("ContentType", "text/plain"),
            "last_modified": str(metadata.get("LastModified", "")),
            "size_bytes": metadata.get("ContentLength", 0),
        }

        # 1) Chunk the text
        chunks = chunk_text(text_content, file_metadata)

        # 2) Save each chunk to S3
        saved_chunks = []
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            chunk_key = f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/chunk_{chunk_id}.json"

            s3_client.put_object(
                Bucket=CHUNKED_TEXT_BUCKET,
                Key=chunk_key,
                Body=json.dumps(chunk, ensure_ascii=False),
                ContentType="application/json",
            )

            saved_chunks.append(
                {
                    "chunk_id": chunk_id,
                    "key": chunk_key,
                    "size": len(json.dumps(chunk, ensure_ascii=False)),
                }
            )

        # 3) Create and save a manifest
        manifest = {
            "source": file_metadata,
            "chunking": {
                "total_chunks": len(chunks),
                "chunk_size": CHUNK_SIZE,
                "chunk_overlap": CHUNK_OVERLAP,
                "chunks": saved_chunks,
            },
            "output": {
                "bucket": CHUNKED_TEXT_BUCKET,
                "prefix": f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/",
            },
        }

        manifest_key = f"{CHUNKED_TEXT_PREFIX}/{filename_without_ext}/manifest.json"
        s3_client.put_object(
            Bucket=CHUNKED_TEXT_BUCKET,
            Key=manifest_key,
            Body=json.dumps(manifest, ensure_ascii=False),
            ContentType="application/json",
        )

        logger.info(f"Successfully processed and chunked {file_key} into {len(chunks)} chunks")
        return {
            "source": {"bucket": bucket_name, "file_key": file_key},
            "output": {
                "bucket": CHUNKED_TEXT_BUCKET,
                "manifest_key": manifest_key,
                "total_chunks": len(chunks),
            },
            "status": "success",
        }

    except Exception as e:
        logger.error(f"Error processing text file {file_key}: {str(e)}")
        raise e


def lambda_handler(event, context):
    """
    Lambda function handler that processes S3 object creation events.
    """
    try:
        logger.info(f"Received event: {json.dumps(event)}")

        results = []
        for record in event.get("Records", []):
            # Process only S3 events
            if record.get("eventSource") != "aws:s3":
                continue

            bucket_name = record.get("s3", {}).get("bucket", {}).get("name")
            file_key = unquote_plus(record.get("s3", {}).get("object", {}).get("key"))

            # Only process .txt files
            if not file_key.lower().endswith(".txt"):
                logger.info(f"Skipping non-text file: {file_key}")
                continue

            result = process_text_file(bucket_name, file_key)
            results.append(result)

        response = {
            "statusCode": 200,
            "body": {
                "message": f"Processed and chunked {len(results)} text files",
                "results": results,
            },
        }
        return response

    except Exception as e:
        logger.error(f"Error in lambda_handler: {str(e)}")
        return {"statusCode": 500, "body": {"message": f"Error processing text files: {str(e)}"}}
