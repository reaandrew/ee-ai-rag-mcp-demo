#!/usr/bin/env python3
# pragma: no cover
"""
Simple JWT token generator for ee-ai-rag-mcp-demo
Using AWS KMS for signing
Also provides a ready-to-use curl command for the API
"""
# IMPORTANT: This script is an admin utility and is not part of the application code.
# It is excluded from test coverage requirements and SonarQube analysis.

import argparse
import json
import os
import time
import uuid
import base64
import boto3
import jwt  # pip install pyjwt

# Constants
ISSUER = "ee-ai-rag-mcp-demo"
KMS_KEY_ALIAS = "alias/ee-ai-rag-mcp-demo-api-token-sign"


def create_jwt_header_payload(expiry_seconds=86400):
    """Create JWT header and payload"""
    issued_at = int(time.time())
    expiration = issued_at + expiry_seconds

    header = {
        "alg": "RS256",
        "typ": "JWT"
    }

    payload = {
        "jti": str(uuid.uuid4()),  # Unique token ID
        "iat": issued_at,          # Issued at timestamp
        "exp": expiration,         # Expiration timestamp
        "iss": ISSUER,             # Issuer
    }

    return header, payload


def get_kms_key_id():
    """Get the KMS key ID from its alias"""
    kms_client = boto3.client("kms")
    
    # List all aliases and find the one with our name
    response = kms_client.list_aliases()
    
    aliases = [alias for alias in response.get("Aliases", []) 
               if alias.get("AliasName") == KMS_KEY_ALIAS]
    
    if not aliases:
        raise ValueError(f"KMS key with alias '{KMS_KEY_ALIAS}' not found.")
    
    return aliases[0].get("TargetKeyId")


def sign_with_kms(message, key_id):
    """Sign a message using AWS KMS"""
    kms_client = boto3.client("kms")
    
    # Encode the message for signing
    message_bytes = message.encode("utf-8")
    
    # Sign the message with KMS
    response = kms_client.sign(
        KeyId=key_id,
        Message=message_bytes,
        MessageType="RAW",
        SigningAlgorithm="RSASSA_PKCS1_V1_5_SHA_256"
    )
    
    # Get the signature
    signature = response["Signature"]
    
    # Convert to base64url encoding
    signature_b64 = base64.urlsafe_b64encode(signature).decode("utf-8").rstrip("=")
    
    return signature_b64


def generate_token(expiry_seconds=86400):
    """Generate a complete JWT token"""
    try:
        # Get KMS key ID
        key_id = get_kms_key_id()
        
        # Create JWT parts
        header, payload = create_jwt_header_payload(expiry_seconds)
        
        # Encode header and payload
        encoded_header = base64.urlsafe_b64encode(json.dumps(header).encode()).decode().rstrip("=")
        encoded_payload = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
        
        # Create unsigned token
        unsigned_token = f"{encoded_header}.{encoded_payload}"
        
        # Sign the token
        signature = sign_with_kms(unsigned_token, key_id)
        
        # Create the complete JWT
        jwt_token = f"{unsigned_token}.{signature}"
        
        return {
            "success": True,
            "token": jwt_token,
            "payload": payload,
            "token_length": len(jwt_token)
        }
        
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }


def get_api_endpoint():
    """Get the API Gateway endpoint from Terraform outputs"""
    try:
        # Create a new session using AWS SDK
        session = boto3.session.Session()
        
        # Initialize a Terraform state client
        s3_client = session.client('s3')
        
        # Try to get the API endpoint from Terraform outputs
        try:
            # Get API endpoint from AWS API Gateway service
            api_client = session.client('apigatewayv2')
            apis = api_client.get_apis()
            
            # Find the policy search API
            api_id = None
            for api in apis.get('Items', []):
                if 'ee-ai-rag-mcp-demo' in api.get('Name', ''):
                    api_id = api.get('ApiId')
                    break
            
            if not api_id:
                return None
            
            # Get the stages for this API
            stages = api_client.get_stages(ApiId=api_id)
            
            # Find the default stage
            stage_name = None
            for stage in stages.get('Items', []):
                if stage.get('StageName') == '$default':
                    stage_name = stage.get('StageName')
                    break
            
            if not stage_name:
                return None
            
            # Construct the API URL
            api_endpoint = f"https://{api_id}.execute-api.{session.region_name}.amazonaws.com/{stage_name}/search"
            return api_endpoint
            
        except Exception as e:
            # Fallback to running the terraform output command
            return None
            
    except Exception as e:
        return None


def format_duration(seconds):
    """Format seconds into human-readable duration"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds // 60} minutes"
    elif seconds < 86400:
        return f"{seconds // 3600} hours"
    else:
        return f"{seconds // 86400} days"


def main():
    """Main function to parse args and generate token"""
    parser = argparse.ArgumentParser(description="Generate a JWT token signed with AWS KMS")
    parser.add_argument("-e", "--expires", type=int, default=86400,
                        help="Token expiration time in seconds (default: 86400, 24 hours)")
    parser.add_argument("-q", "--query", type=str, 
                        help="Optional query to include in the generated curl command")
    args = parser.parse_args()
    
    print("Generating and signing JWT with KMS...")
    result = generate_token(args.expires)
    
    if not result["success"]:
        print(f"Error generating JWT token: {result['error']}")
        return 1
    
    # Extract values
    jwt_token = result["token"]
    payload = result["payload"]
    token_length = result["token_length"]
    
    # Get API endpoint
    api_endpoint = get_api_endpoint()
    if not api_endpoint:
        # Use the terraform command to get the API URL
        try:
            import subprocess
            # Try getting terraform outputs
            terraform_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                        'terraform', 'app')
            os.chdir(terraform_dir)
            process = subprocess.Popen(["terraform", "output", "-json"], 
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            stdout, stderr = process.communicate()
            if process.returncode == 0:
                outputs = json.loads(stdout)
                api_endpoint = outputs.get("policy_search_api_url", {}).get("value", "")
            else:
                api_endpoint = "[YOUR-API-ENDPOINT]"
        except Exception:
            api_endpoint = "[YOUR-API-ENDPOINT]"
    
    # Display token information
    print("JWT Token successfully generated")
    print("-------------------------------")
    print(f"Issuer:      {ISSUER}")
    print(f"Token ID:    {payload['jti']}")
    print(f"Issued at:   {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload['iat']))}")
    print(f"Expires at:  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload['exp']))} (valid for {format_duration(args.expires)})")
    print(f"Token length: {token_length} characters")
    print("-------------------------------")
    print(f"Token: {jwt_token}")
    print("-------------------------------")
    
    # Generate curl command
    print("CURL COMMAND FOR API REQUEST:")
    
    query = args.query if args.query else "What is our password policy?"
    query_json = json.dumps({"query": query})
    
    curl_cmd = (
        f"curl -X POST \\\n"
        f"  -H \"Content-Type: application/json\" \\\n"
        f"  -H \"Authorization: {jwt_token}\" \\\n"
        f"  -d '{query_json}' \\\n"
        f"  {api_endpoint}"
    )
    
    print(curl_cmd)
    print("-------------------------------")
    
    # Create a sample shell script
    script_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "query_api.sh")
    with open(script_path, "w") as f:
        f.write(f"""#!/bin/bash
# Generated by generate_api_token.py on {time.strftime('%Y-%m-%d %H:%M:%S')}

API_URL="{api_endpoint}"
AUTH_TOKEN="{jwt_token}"

# Function to make API call
query_api() {{
  local query="$1"
  
  # Create temporary file for request body
  TMPFILE=$(mktemp)
  echo "{{\\"query\\": \\"$query\\"}}" > $TMPFILE
  
  # Make the API call
  curl -X POST \\
    -H "Content-Type: application/json" \\
    -H "Authorization: $AUTH_TOKEN" \\
    --data @$TMPFILE \\
    "$API_URL"
    
  # Clean up temp file
  rm $TMPFILE
}}

# Check if query was provided as argument
if [ $# -eq 0 ]; then
  echo "Usage: $0 \\"your policy question here\\""
  echo "Example: $0 \\"What is our password policy?\\""
  exit 1
fi

# Execute query
query_api "$1"
""")
    
    # Use more secure permissions (user read+write+execute only)
    os.chmod(script_path, 0o700)
    print(f"Shell script created: {script_path}")
    print(f"Usage: {script_path} \"Your question here\"")
    
    return 0


if __name__ == "__main__":
    exit(main())