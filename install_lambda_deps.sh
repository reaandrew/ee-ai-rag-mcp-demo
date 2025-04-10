#!/bin/bash
set -e

# Create package directory
mkdir -p package/python

# Install minimal dependencies directly (no requirements.txt)
echo "Installing dependencies for Lambda layers..."
pip install --target package/python langchain-text-splitters==0.3.8 pydantic==2.11.3 regex opensearch-py==2.0.0 requests-aws4auth==1.1.0

# Clean up unnecessary files to reduce size
echo "Cleaning up to reduce layer size..."
find package -type d -name "__pycache__" -exec rm -rf {} +
find package -type d -name "tests" -exec rm -rf {} + 2>/dev/null || true
find package -type d -name "test" -exec rm -rf {} + 2>/dev/null || true
find package -type f -name "*.pyc" -delete
find package -type f -name "*.pyo" -delete
find package -type f -name "*.md" -delete 2>/dev/null || true
find package -type f -name "*.rst" -delete 2>/dev/null || true
find package -type f -name "LICENSE*" -delete 2>/dev/null || true

# Create the zip files
mkdir -p build
cd package
zip -r "../build/text-chunker-layer.zip" * -r
cp "../build/text-chunker-layer.zip" "../build/vector-generator-layer.zip"
cp "../build/text-chunker-layer.zip" "../build/policy-search-layer.zip"
cd ..

# Display the size of the layers
echo "Text chunker layer size: $(du -h build/text-chunker-layer.zip | cut -f1)"
echo "Vector generator layer size: $(du -h build/vector-generator-layer.zip | cut -f1)"
echo "Policy search layer size: $(du -h build/policy-search-layer.zip | cut -f1)"
echo "Lambda layers packaged successfully"