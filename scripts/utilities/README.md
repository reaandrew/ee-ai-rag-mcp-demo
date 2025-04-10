# OpenSearch Utility Scripts

This directory contains utility scripts for working with OpenSearch.

## Setup

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Available Scripts

### count_opensearch_objects.py

Counts the number of documents in an OpenSearch domain.

#### Usage

Basic usage (counts documents in the default index 'rag-vectors'):

```bash
./count_opensearch_objects.py
```

Count documents in all indices:

```bash
./count_opensearch_objects.py --index all
```

Count documents in a specific index:

```bash
./count_opensearch_objects.py --index my-custom-index
```

#### Authentication Options

The script supports two authentication methods:

1. IAM Authentication (default):

```bash
./count_opensearch_objects.py --auth-method iam
```

2. Username/Password from AWS Secrets Manager:

```bash
./count_opensearch_objects.py --auth-method secret --secret-name my/secret/name
```

#### Additional Options

```
--domain DOMAIN       OpenSearch domain name (default: ee-ai-rag-mcp-demo-vectors)
--region REGION       AWS region (default: eu-west-2)
--verbose, -v         Enable verbose output
```

For help:

```bash
./count_opensearch_objects.py --help
```