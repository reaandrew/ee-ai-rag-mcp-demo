#!/bin/bash
set -e

# Function to build a Lambda package with dependencies
build_lambda_package() {
    local lambda_name=$1
    local source_dir="src/lambda_functions/$lambda_name"
    local build_dir="build/$lambda_name"
    local zip_name=$(echo "$lambda_name" | tr '_' '-')
    local zip_file="build/$zip_name.zip"
    
    echo "Building Lambda package for $lambda_name..."
    
    # Create build directory
    mkdir -p "$build_dir"
    
    # Copy Lambda source files
    cp -R "$source_dir"/* "$build_dir"/
    
    # Copy utils module for lambda functions that need it
    if [[ "$lambda_name" == "policy_search" || "$lambda_name" == "vector_generator" ]]; then
        echo "Copying utils module for $lambda_name..."
        mkdir -p "$build_dir/utils"
        cp -R "src/utils"/* "$build_dir/utils/"
        # Ensure __init__.py exists
        touch "$build_dir/utils/__init__.py"
        
        # Fix import paths in handlers for Lambda environment
        echo "Fixing imports in handler.py for $lambda_name..."
        sed -i 's/from src\.utils/from utils/g' "$build_dir/handler.py"
        
        # Log the structure for debugging
        echo "Utils module structure:"
        find "$build_dir/utils" -type f | sort
    fi
    
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
build_lambda_package "vector_generator"
build_lambda_package "policy_search"
build_lambda_package "auth_authorizer"

echo "All Lambda packages built successfully"