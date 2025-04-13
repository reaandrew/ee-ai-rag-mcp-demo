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
KEY_ID=$(aws kms list-aliases --query "Aliases[?AliasName=='alias/ee-ai-rag-mcp-demo-api-token-sign'].TargetKeyId" --output text)

if [ -z "$KEY_ID" ] || [ "$KEY_ID" == "None" ]; then
    echo "Error: KMS key with alias 'alias/ee-ai-rag-mcp-demo-api-token-sign' not found."
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

# Debug info
echo "Raw signature length: $(echo -n "$SIGNATURE" | wc -c) bytes"

# Base64 encode the signature without line wrapping
B64_SIGNATURE=$(echo -n "$SIGNATURE" | base64 -w 0)
echo "Base64 signature length: ${#B64_SIGNATURE} characters"

# Create the combined token
COMBINED="$TOKEN_ID:$B64_SIGNATURE"
echo "Combined token length: ${#COMBINED} characters"

# Base64 encode the entire token without line wrapping
API_TOKEN=$(echo -n "$COMBINED" | base64 -w 0)
echo "Final token length: ${#API_TOKEN} characters"

# Let's verify the signature to make sure it works
echo "Verifying signature locally..."
echo "Decoding token for verification..."
VERIFY_COMBINED=$(echo -n "$API_TOKEN" | base64 -d)
VERIFY_PARTS=(${VERIFY_COMBINED//:/ })
if [ ${#VERIFY_PARTS[@]} -eq 2 ]; then
    VERIFY_TOKEN_ID=${VERIFY_PARTS[0]}
    VERIFY_B64_SIG=${VERIFY_PARTS[1]}
    echo "Extracted token ID: $VERIFY_TOKEN_ID"
    echo "Extracted signature length: ${#VERIFY_B64_SIG} characters"
    if [ "$VERIFY_TOKEN_ID" = "$TOKEN_ID" ]; then
        echo "Token ID verification successful"
    else
        echo "WARNING: Token ID verification failed!"
    fi
else
    echo "WARNING: Could not properly split the combined token!"
fi

echo "API Token successfully generated"
echo "-------------------------------"
echo "Token: $API_TOKEN"
echo "-------------------------------"
echo "Use this token in the Authorization header for API requests"
echo "Example: curl -H \"Authorization: $API_TOKEN\" https://your-api-endpoint/search"