#!/bin/bash

# Generate a JWT token using AWS KMS and Node.js
# This creates a token with expiration time, signed with KMS RSA

set -e

# Display usage info
function show_usage {
    echo "Usage: $0 [options]"
    echo ""
    echo "Options:"
    echo "  -e, --expires <seconds>  Token expiration time in seconds (default: 86400, 24 hours)"
    echo "  -h, --help               Display this help message and exit"
    echo ""
    echo "Example:"
    echo "  $0 --expires 3600        Generate a token valid for 1 hour"
}

# Process command line arguments
EXPIRY_TIME=86400  # Default: 24 hours

while [[ $# -gt 0 ]]; do
    case "$1" in
        -e|--expires)
            if [[ $2 =~ ^[0-9]+$ ]]; then
                EXPIRY_TIME=$2
                shift 2
            else
                echo "Error: Expiration time must be a number in seconds"
                show_usage
                exit 1
            fi
            ;;
        -h|--help)
            show_usage
            exit 0
            ;;
        *)
            echo "Error: Unknown option: $1"
            show_usage
            exit 1
            ;;
    esac
done

# Check if required tools are installed
for cmd in aws jq node; do
    if ! command -v $cmd &> /dev/null; then
        echo "Error: $cmd is not installed. Please install it first."
        exit 1
    fi
done

# Check if required npm packages are installed locally
if [ ! -d "node_modules/jsonwebtoken" ] || [ ! -d "node_modules/uuid" ]; then
    echo "Installing required npm packages..."
    npm install --no-save jsonwebtoken uuid
fi

# Check if the KMS key alias exists
KEY_ID=$(aws kms list-aliases --query "Aliases[?AliasName=='alias/ee-ai-rag-mcp-demo-api-token-sign'].TargetKeyId" --output text)

if [ -z "$KEY_ID" ] || [ "$KEY_ID" == "None" ]; then
    echo "Error: KMS key with alias 'alias/ee-ai-rag-mcp-demo-api-token-sign' not found."
    echo "Please deploy the infrastructure first."
    exit 1
fi

# Get current timestamp and calculate expiration
ISSUED_AT=$(date +%s)
EXPIRATION=$((ISSUED_AT + EXPIRY_TIME))

# Create a temporary Node.js script to generate and sign the JWT
TMP_SCRIPT=$(mktemp)
cat > "$TMP_SCRIPT" << 'EOF'
const fs = require('fs');
const jwt = require('jsonwebtoken');
const { v4: uuidv4 } = require('uuid');
const { execSync } = require('child_process');

// Get arguments from environment
const keyId = process.env.KEY_ID;
const issuedAt = parseInt(process.env.ISSUED_AT, 10);
const expiration = parseInt(process.env.EXPIRATION, 10);

// Create JWT payload
const payload = {
  jti: uuidv4(),              // Unique token ID
  iat: issuedAt,              // Issued at timestamp
  exp: expiration,            // Expiration timestamp
  iss: 'ee-ai-rag-mcp-demo',  // Issuer
};

try {
  // First, create the JWT header and payload parts
  const header = { alg: 'RS256', typ: 'JWT' };
  const encodedHeader = Buffer.from(JSON.stringify(header)).toString('base64url');
  const encodedPayload = Buffer.from(JSON.stringify(payload)).toString('base64url');
  const unsignedToken = `${encodedHeader}.${encodedPayload}`;

  // Save the message to sign to a temporary file
  fs.writeFileSync('/tmp/jwt_to_sign.txt', unsignedToken);

  // Use AWS KMS to sign the message
  const signCommand = `aws kms sign \
    --key-id "${keyId}" \
    --message-type RAW \
    --signing-algorithm RSASSA_PKCS1_V1_5_SHA_256 \
    --message fileb:///tmp/jwt_to_sign.txt \
    --output json`;

  const signResult = JSON.parse(execSync(signCommand).toString());
  const signature = Buffer.from(signResult.Signature, 'base64').toString('base64url');

  // Combine to create the final JWT
  const jwtToken = `${unsignedToken}.${signature}`;

  // Create result object
  const result = {
    success: true,
    token: jwtToken,
    payload: payload,
    tokenLength: jwtToken.length
  };

  console.log(JSON.stringify(result));
} catch (error) {
  // Handle errors
  console.log(JSON.stringify({
    success: false,
    error: error.message || 'Unknown error occurred'
  }));
  process.exit(1);
}
EOF

# Execute the Node.js script with the necessary environment variables
echo "Generating and signing JWT with KMS..."
RESULT=$(KEY_ID="$KEY_ID" ISSUED_AT="$ISSUED_AT" EXPIRATION="$EXPIRATION" node "$TMP_SCRIPT")

# Check if the operation was successful
SUCCESS=$(echo "$RESULT" | jq -r '.success')
if [ "$SUCCESS" != "true" ]; then
    ERROR=$(echo "$RESULT" | jq -r '.error')
    echo "Error generating JWT token: $ERROR"
    # Clean up and exit
    rm -f /tmp/jwt_to_sign.txt "$TMP_SCRIPT"
    exit 1
fi

# Parse the result
JWT_TOKEN=$(echo "$RESULT" | jq -r '.token')
TOKEN_ID=$(echo "$RESULT" | jq -r '.payload.jti')
TOKEN_LENGTH=$(echo "$RESULT" | jq -r '.tokenLength')

# Calculate human-readable duration
if [ $EXPIRY_TIME -lt 60 ]; then
    EXPIRY_HUMAN="${EXPIRY_TIME} seconds"
elif [ $EXPIRY_TIME -lt 3600 ]; then
    EXPIRY_HUMAN="$((EXPIRY_TIME / 60)) minutes"
elif [ $EXPIRY_TIME -lt 86400 ]; then
    EXPIRY_HUMAN="$((EXPIRY_TIME / 3600)) hours"
else
    EXPIRY_HUMAN="$((EXPIRY_TIME / 86400)) days"
fi

# Display token information
echo "JWT Token successfully generated"
echo "-------------------------------"
echo "Issuer:      ee-ai-rag-mcp-demo"
echo "Token ID:    $TOKEN_ID"
echo "Issued at:   $(date -d @$ISSUED_AT)"
echo "Expires at:  $(date -d @$EXPIRATION) (valid for $EXPIRY_HUMAN)"
echo "Token length: $TOKEN_LENGTH characters"
echo "-------------------------------"
echo "Token: $JWT_TOKEN"
echo "-------------------------------"
echo "Use this token in the Authorization header for API requests"
echo "Example: curl -H \"Authorization: $JWT_TOKEN\" https://your-api-endpoint/search"

# Clean up temporary files
rm -f /tmp/jwt_to_sign.txt "$TMP_SCRIPT"