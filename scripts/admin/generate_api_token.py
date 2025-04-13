#!/usr/bin/env python3
"""
Simple JWT token generator for ee-ai-rag-mcp-demo
Using AWS KMS for signing
"""

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
    print("Use this token in the Authorization header for API requests")
    print(f"Example: curl -H \"Authorization: {jwt_token}\" https://your-api-endpoint/search")
    
    return 0


if __name__ == "__main__":
    exit(main())