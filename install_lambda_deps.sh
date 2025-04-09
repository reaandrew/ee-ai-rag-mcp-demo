#!/bin/bash
set -e

# Set up directories
LAMBDA_DIR="src/lambda_functions/text_chunker"
DEPS_DIR="$LAMBDA_DIR/dependencies"
mkdir -p $DEPS_DIR/python

# Install dependencies for the text_chunker lambda
echo "Installing dependencies for text_chunker..."
pip install -r $LAMBDA_DIR/requirements.txt -t $DEPS_DIR/python

# Create the layer zip file
mkdir -p build
CURRENT_DIR=$(pwd)
cd $DEPS_DIR
zip -r "$CURRENT_DIR/build/text-chunker-layer.zip" python
cd "$CURRENT_DIR"

echo "Lambda layer packaged successfully"