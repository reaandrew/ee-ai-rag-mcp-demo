# ee-ai-rag-mcp-demo

A repository with conventional commit enforcement, automatic versioning, and SonarQube code quality checks. This project implements a RAG (Retrieval Augmented Generation) pattern using AWS Services including Lambda, OpenSearch, and Amazon Bedrock.

## Quality Gates with SonarQube

This repository uses SonarQube for quality checks:

1. **PR Quality Gate**: Runs SonarQube analysis on all PRs to the main branch
2. **Main Branch Quality Gate**: Runs analysis after merges to main
3. **Release Protection**: Version tags are only created if SonarQube checks pass

### Setup Requirements

1. Create a SonarCloud account at https://sonarcloud.io/
2. Create or join a SonarCloud organization named "reaandrew"
3. Create a new project with key "reaandrew_ee-ai-rag-mcp-demo" in SonarCloud
4. Add the following secrets to your GitHub repository:
   - `SONAR_TOKEN`: Your SonarCloud API token

### Configuration

The SonarCloud configuration is simplifies using the standard approach:
- Configuration is stored in sonar-project.properties
- Uses SonarSource's official GitHub Actions
- Works with both PR analysis and branch analysis

## Conventional Commits

This repository uses [Conventional Commits](https://www.conventionalcommits.org/) to standardize commit messages and automate versioning.

### Commit Format

Each commit message should follow this format:

```
<type>[optional scope]: <description>

[optional body]

[optional footer(s)]
```

Examples:
- `feat: add new feature`
- `fix: resolve login bug`
- `docs: update README`
- `chore(deps): update dependencies`

### Common Types

- `feat`: A new feature
- `fix`: A bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, etc.)
- `refactor`: Code changes that neither fix bugs nor add features
- `perf`: Performance improvements
- `test`: Adding or correcting tests
- `chore`: Changes to the build process or auxiliary tools

## Automatic Versioning

This repository uses [semantic-release](https://github.com/semantic-release/semantic-release) to automatically version and tag releases based on commit messages:

- `feat:` commits trigger a minor version bump (1.0.0 → 1.1.0)
- `fix:` commits trigger a patch version bump (1.0.0 → 1.0.1)
- `feat!:` or commits with `BREAKING CHANGE:` in the footer trigger a major version bump (1.0.0 → 2.0.0)

## Setup

Run the following to set up the commit hooks locally:

```bash
npm install
```

## Architecture Overview

This project implements a RAG (Retrieval Augmented Generation) pipeline with the following components:

1. **Document Ingestion**:
   - PDF documents are uploaded to an S3 bucket
   - A Lambda function extracts text from the PDFs using AWS Textract

2. **Text Processing**:
   - Extracted text is chunked into smaller segments by another Lambda function
   - Each chunk is stored in a dedicated S3 bucket

3. **Vector Generation and Storage**:
   - The vector_generator Lambda processes each text chunk
   - Vector embeddings are generated using Amazon Bedrock's Titan model
   - Embeddings are stored in Amazon OpenSearch for efficient vector search

4. **Search and Retrieval**:
   - OpenSearch provides vector similarity search capabilities
   - The stored vectors can be queried to find semantically similar content

### Infrastructure

The infrastructure is deployed using Terraform and includes:

- S3 buckets for document storage at various processing stages
- Lambda functions for text extraction, chunking, and vector generation
- OpenSearch domain for vector storage and similarity search
- IAM roles and policies for secure service interactions
- CloudWatch logging for monitoring and debugging

### Using with RAG Applications

To integrate with your RAG applications:

1. Upload PDF documents to the raw PDFs S3 bucket
2. The system automatically processes documents and generates vector embeddings
3. Query the OpenSearch domain to perform semantic searches
4. Retrieve relevant text chunks to provide context to your LLM

For details on the OpenSearch configuration and how to query the vectors, refer to the AWS OpenSearch documentation.

## Future Improvements

- Improve test coverage for utility modules:
  - Create comprehensive tests for `src/utils/bedrock_utils.py` (current coverage: 0%)
  - Create comprehensive tests for `src/utils/opensearch_utils.py` (current coverage: 0%)
  - Target at least 80% coverage for these modules