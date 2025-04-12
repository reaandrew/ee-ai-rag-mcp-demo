#!/bin/bash

# Generate an API token using KMS signing
# This script creates a new UUID token, signs it with KMS, and formats it as a base64-encoded string

set -e

# Check if AWS CLI is installed
if ! command -v aws &> /dev/null; then
    echo "Error: AWS CLI is not installed. Please install it first."
    exit 1
fi

# Check if the KMS key alias exists
KEY_ID=$(aws kms list-aliases --query "Aliases[?AliasName=='alias/ee-ai-rag-mcp-demo-api-token'].TargetKeyId" --output text)

if [ -z "$KEY_ID" ] || [ "$KEY_ID" == "None" ]; then
    echo "Error: KMS key with alias 'alias/ee-ai-rag-mcp-demo-api-token' not found."
    echo "Please deploy the infrastructure first."
    exit 1
fi

# Generate a random UUID for the token
TOKEN_ID=$(uuidgen)
echo "Generated token ID: $TOKEN_ID"

# Sign the token with KMS
echo "Signing token with KMS..."
SIGNATURE=$(aws kms sign \
    --key-id $KEY_ID \
    --message-type RAW \
    --signing-algorithm RSASSA_PKCS1_V1_5_SHA_256 \
    --message "$TOKEN_ID" \
    --output text \
    --query Signature)

# Base64 encode the signature
B64_SIGNATURE=$(echo -n "$SIGNATURE" | base64)

# Create the combined token
COMBINED="$TOKEN_ID:$B64_SIGNATURE"

# Base64 encode the entire token
API_TOKEN=$(echo -n "$COMBINED" | base64)

echo "API Token successfully generated"
echo "-------------------------------"
echo "Token: $API_TOKEN"
echo "-------------------------------"
echo "Use this token in the Authorization header for API requests"
echo "Example: curl -H \"Authorization: $API_TOKEN\" https://your-api-endpoint/search"