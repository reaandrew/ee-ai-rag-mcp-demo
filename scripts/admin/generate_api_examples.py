#!/usr/bin/env python3
# pragma: no cover
"""
API example generator for ee-ai-rag-mcp-demo
Provides JWT token generation and ready-to-use curl commands for all APIs
"""
# IMPORTANT: This script is an admin utility and is not part of the application code.
# It is excluded from test coverage requirements and SonarQube analysis.

import argparse
import json
import os
import time
import uuid
import boto3
import jwt  # pip install pyjwt

# Constants
ISSUER = "ee-ai-rag-mcp-demo"
KMS_KEY_ALIAS = "alias/ee-ai-rag-mcp-demo-api-token-symmetric"


def create_jwt_payload(expiry_seconds=86400):
    """Create JWT payload"""
    issued_at = int(time.time())
    expiration = issued_at + expiry_seconds

    payload = {
        "jti": str(uuid.uuid4()),  # Unique token ID
        "iat": issued_at,          # Issued at timestamp
        "exp": expiration,         # Expiration timestamp
        "iss": ISSUER,             # Issuer
    }

    return payload


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


def generate_token(expiry_seconds=86400):
    """Generate a complete JWT token using KMS for HMAC signing"""
    try:
        # Get KMS key ID
        key_id = get_kms_key_id()
        
        # Create JWT payload
        payload = create_jwt_payload(expiry_seconds)
        
        # Use PyJWT with the 'kms' algorithm and key_id
        # PyJWT will handle the encoding and signing
        jwt_token = jwt.encode(
            payload,
            key_id,  # The KMS key ID
            algorithm="HS256",
            headers={"kid": key_id}
        )
        
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


def get_terraform_outputs():
    """Get all API endpoints from Terraform outputs"""
    try:
        # Use the terraform command to get the API URLs
        terraform_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 
                                    'terraform', 'app')
        os.chdir(terraform_dir)
        import subprocess
        process = subprocess.Popen(["terraform", "output", "-json"], 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        stdout, stderr = process.communicate()
        
        if process.returncode == 0:
            return json.loads(stdout)
        else:
            print(f"Error running terraform output: {stderr.decode()}")
            return {}
            
    except Exception as e:
        print(f"Error getting terraform outputs: {str(e)}")
        return {}


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
    """Main function to parse args and generate example API calls"""
    parser = argparse.ArgumentParser(description="Generate JWT token and API examples")
    parser.add_argument("-e", "--expires", type=int, default=86400,
                        help="Token expiration time in seconds (default: 86400, 24 hours)")
    parser.add_argument("-q", "--query", type=str, default="What is our password policy?",
                        help="Query for the policy search API example")
    parser.add_argument("-d", "--doc-id", type=str, default="example-bucket/example.pdf",
                        help="Document ID for the document status API example")
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
    
    # Get API endpoints from Terraform outputs
    terraform_outputs = get_terraform_outputs()
    
    policy_search_api_url = terraform_outputs.get("policy_search_api_url", {}).get("value", "[POLICY-SEARCH-API-ENDPOINT]")
    document_status_api_url = terraform_outputs.get("document_status_api_url", {}).get("value", "[DOCUMENT-STATUS-API-ENDPOINT]")
    
    # Display token information
    print("\n" + "="*50)
    print("JWT TOKEN INFORMATION")
    print("="*50)
    print(f"Issuer:      {ISSUER}")
    print(f"Token ID:    {payload['jti']}")
    print(f"Issued at:   {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload['iat']))}")
    print(f"Expires at:  {time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(payload['exp']))} (valid for {format_duration(args.expires)})")
    print(f"Token length: {token_length} characters")
    print("-"*50)
    print(f"Token: {jwt_token}")
    print("="*50)
    
    # Generate Policy Search API curl command
    print("\n" + "="*50)
    print("POLICY SEARCH API EXAMPLES")
    print("="*50)
    
    query = args.query
    query_json = json.dumps({"query": query})
    
    policy_search_curl = (
        f"# Policy Search API - POST /search\n"
        f"curl -X POST \\\n"
        f"  -H \"Content-Type: application/json\" \\\n"
        f"  -H \"Authorization: {jwt_token}\" \\\n"
        f"  -d '{query_json}' \\\n"
        f"  {policy_search_api_url}"
    )
    
    print(policy_search_curl)
    print("="*50)
    
    # Generate Document Status API curl commands
    print("\n" + "="*50)
    print("DOCUMENT STATUS API EXAMPLES")
    print("="*50)
    
    doc_id = args.doc_id
    
    # GET with path parameter
    doc_status_path_curl = (
        f"# Document Status API - GET /status/{doc_id}\n"
        f"curl -X GET \\\n"
        f"  -H \"Authorization: {jwt_token}\" \\\n"
        f"  {document_status_api_url}/{doc_id}"
    )
    
    # GET with query parameter
    doc_status_query_curl = (
        f"# Document Status API - GET /status?document_id={doc_id}\n"
        f"curl -X GET \\\n"
        f"  -H \"Authorization: {jwt_token}\" \\\n"
        f"  \"{document_status_api_url}?document_id={doc_id}\""
    )
    
    # GET with query parameter and use_base_id=false
    doc_status_query_base_curl = (
        f"# Document Status API - GET /status?document_id={doc_id}&use_base_id=false\n"
        f"curl -X GET \\\n"
        f"  -H \"Authorization: {jwt_token}\" \\\n"
        f"  \"{document_status_api_url}?document_id={doc_id}&use_base_id=false\""
    )
    
    # POST with body
    doc_status_body_json = json.dumps({"document_id": doc_id, "use_base_id": True})
    doc_status_post_curl = (
        f"# Document Status API - POST /status\n"
        f"curl -X POST \\\n"
        f"  -H \"Content-Type: application/json\" \\\n"
        f"  -H \"Authorization: {jwt_token}\" \\\n"
        f"  -d '{doc_status_body_json}' \\\n"
        f"  {document_status_api_url}"
    )
    
    print(doc_status_path_curl)
    print("\n" + "-"*50 + "\n")
    print(doc_status_query_curl)
    print("\n" + "-"*50 + "\n")
    print(doc_status_query_base_curl)
    print("\n" + "-"*50 + "\n")
    print(doc_status_post_curl)
    print("="*50)
    
    return 0


if __name__ == "__main__":
    exit(main())