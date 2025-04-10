#!/usr/bin/env python3
"""
Utility script to query the number of objects/documents in OpenSearch.
This script connects to the OpenSearch domain and reports the count of documents
across all indices or for a specific index.
"""

import argparse
import boto3
import os
import json
import logging
from opensearchpy import OpenSearch, RequestsHttpConnection
from requests_aws4auth import AWS4Auth

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger('opensearch-count')

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Count documents in OpenSearch')
    parser.add_argument('--domain', type=str, default=os.environ.get('OPENSEARCH_DOMAIN', 'ee-ai-rag-mcp-demo-vectors'),
                        help='OpenSearch domain name')
    parser.add_argument('--region', type=str, default=os.environ.get('AWS_REGION', 'eu-west-2'),
                        help='AWS region')
    parser.add_argument('--index', type=str, default='rag-vectors',
                        help='OpenSearch index name (default: rag-vectors, use "all" for all indices)')
    parser.add_argument('--verbose', '-v', action='store_true',
                        help='Enable verbose output')
    parser.add_argument('--auth-method', type=str, choices=['iam', 'secret'], default='iam',
                        help='Authentication method (iam or secret)')
    parser.add_argument('--secret-name', type=str, 
                        default='ee-ai-rag-mcp-demo/opensearch-master-credentials-v2',
                        help='AWS Secrets Manager secret name (for secret auth method)')
    return parser.parse_args()

def get_opensearch_client(domain, region, auth_method='iam', secret_name=None):
    """
    Create and return an OpenSearch client.
    
    Args:
        domain (str): OpenSearch domain name
        region (str): AWS region
        auth_method (str): Authentication method ('iam' or 'secret')
        secret_name (str): AWS Secrets Manager secret name (only for 'secret' auth method)
        
    Returns:
        OpenSearch client
    """
    host = f"{domain}.{region}.es.amazonaws.com"
    
    if auth_method == 'iam':
        # Use IAM authentication
        credentials = boto3.Session().get_credentials()
        awsauth = AWS4Auth(
            credentials.access_key,
            credentials.secret_key,
            region,
            'es',
            session_token=credentials.token
        )
        
        client = OpenSearch(
            hosts=[{'host': host, 'port': 443}],
            http_auth=awsauth,
            use_ssl=True,
            verify_certs=True,
            connection_class=RequestsHttpConnection,
            timeout=30
        )
        
    elif auth_method == 'secret':
        # Use username/password from Secrets Manager
        secrets_client = boto3.client('secretsmanager', region_name=region)
        try:
            response = secrets_client.get_secret_value(SecretId=secret_name)
            secret = json.loads(response['SecretString'])
            username = secret.get('username')
            password = secret.get('password')
            
            client = OpenSearch(
                hosts=[{'host': host, 'port': 443}],
                http_auth=(username, password),
                use_ssl=True,
                verify_certs=True,
                connection_class=RequestsHttpConnection,
                timeout=30
            )
            
        except Exception as e:
            logger.error(f"Error retrieving credentials from Secrets Manager: {str(e)}")
            raise
            
    else:
        raise ValueError(f"Invalid auth_method: {auth_method}")
    
    return client

def count_documents(client, index=None):
    """
    Count documents in the specified index or across all indices.
    
    Args:
        client: OpenSearch client
        index (str): Index name or 'all' for all indices
        
    Returns:
        dict: Document counts by index
    """
    results = {}
    
    if index and index.lower() != 'all':
        # Count documents in the specified index
        try:
            response = client.count(index=index)
            results[index] = response['count']
        except Exception as e:
            logger.error(f"Error counting documents in index {index}: {str(e)}")
            results[index] = f"ERROR: {str(e)}"
    else:
        # Get all indices
        try:
            indices = client.indices.get('*')
            
            # Count documents in each index
            for idx in indices:
                try:
                    response = client.count(index=idx)
                    results[idx] = response['count']
                except Exception as e:
                    logger.error(f"Error counting documents in index {idx}: {str(e)}")
                    results[idx] = f"ERROR: {str(e)}"
        except Exception as e:
            logger.error(f"Error retrieving indices: {str(e)}")
            results['ERROR'] = str(e)
    
    return results

def display_results(results, verbose=False):
    """
    Display document count results.
    
    Args:
        results (dict): Document counts by index
        verbose (bool): Whether to show detailed output
    """
    total_docs = 0
    
    # Print header
    print("\n" + "="*60)
    print(f"{'INDEX':<40} {'COUNT':>10}")
    print("="*60)
    
    # Print counts for each index
    for index, count in sorted(results.items()):
        if isinstance(count, int):
            total_docs += count
            print(f"{index:<40} {count:>10,}")
        else:
            # Error case
            print(f"{index:<40} {count}")
    
    # Print total
    print("="*60)
    print(f"{'TOTAL DOCUMENTS':<40} {total_docs:>10,}")
    print("="*60 + "\n")
    
    if verbose:
        print("Raw response:")
        print(json.dumps(results, indent=2))
        print("\n")

def main():
    """Main entry point."""
    args = parse_args()
    
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    
    try:
        # Get OpenSearch client
        client = get_opensearch_client(
            args.domain, 
            args.region, 
            auth_method=args.auth_method,
            secret_name=args.secret_name
        )
        
        # Count documents
        index_to_query = args.index if args.index.lower() != 'all' else None
        results = count_documents(client, index=index_to_query)
        
        # Display results
        display_results(results, verbose=args.verbose)
        
    except Exception as e:
        logger.error(f"An error occurred: {str(e)}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())