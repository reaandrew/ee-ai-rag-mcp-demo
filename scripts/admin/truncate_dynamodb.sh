#!/usr/bin/env bash

aws dynamodb scan --table-name ee-ai-rag-mcp-demo-doc-tracking > items.json

# Step 2: Extract the document IDs using jq and save to a file
jq -r '.Items[].document_id.S' items.json > doc_ids.txt

# Step 3: Delete each item
while read id; do
  aws dynamodb delete-item --table-name ee-ai-rag-mcp-demo-doc-tracking --key "{\"document_id\":{\"S\":\"$id\"}}"
  echo "Deleted item with ID: $id"
done < doc_ids.txt

# Step 4: Clean up temporary files
rm items.json doc_ids.txt

