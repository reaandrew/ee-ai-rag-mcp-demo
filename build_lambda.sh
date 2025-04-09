#!/bin/bash
set -e

# Function to build a Lambda package with dependencies
build_lambda_package() {
    local lambda_name=$1
    local source_dir="src/lambda_functions/$lambda_name"
    local build_dir="build/$lambda_name"
    local zip_file="build/$lambda_name.zip"
    
    echo "Building Lambda package for $lambda_name..."
    
    # Create build directory
    mkdir -p "$build_dir"
    
    # Copy Lambda source files
    cp -R "$source_dir"/* "$build_dir"/
    
    # Install dependencies if requirements.txt exists
    if [ -f "$build_dir/requirements.txt" ]; then
        echo "Installing dependencies for $lambda_name..."
        pip install -r "$build_dir/requirements.txt" -t "$build_dir"
    fi
    
    # Remove unnecessary files
    find "$build_dir" -type d -name "__pycache__" -exec rm -rf {} +
    find "$build_dir" -type f -name "*.pyc" -delete
    find "$build_dir" -type f -name "*.pyo" -delete
    find "$build_dir" -type f -name "*.pyd" -delete
    
    # Create zip file
    echo "Creating zip file $zip_file..."
    cd "$build_dir" && zip -r "../../$zip_file" . && cd ../..
    
    echo "Lambda package for $lambda_name built successfully"
}

# Ensure build directory exists
mkdir -p build

# Build Lambda packages
build_lambda_package "text_extractor"
build_lambda_package "text_chunker"

echo "All Lambda packages built successfully"