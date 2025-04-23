#!/usr/bin/env python3
"""
Render Jinja2 templates for UI files with API endpoints.
Used during CI/CD to inject the correct API endpoints into UI templates.
"""

import os
import sys
import argparse
import json
from jinja2 import Environment, FileSystemLoader

def render_template(template_path, output_path, context):
    """
    Render a jinja2 template with the provided context and save to the output path.
    
    Args:
        template_path (str): Path to the template file or directory containing templates
        output_path (str): Path where the rendered files will be saved
        context (dict): Variables to use in template rendering
    """
    # Get the directory and filename
    template_dir = os.path.dirname(template_path)
    template_file = os.path.basename(template_path)
    
    # Create Jinja2 environment
    env = Environment(loader=FileSystemLoader(template_dir))
    template = env.get_template(template_file)
    
    # Render the template
    rendered_content = template.render(**context)
    
    # Create output directory if it doesn't exist
    output_dir = os.path.dirname(output_path)
    if output_dir:  # Only try to create directory if there's a parent directory
        os.makedirs(output_dir, exist_ok=True)
    
    # Write the rendered content to the output file
    with open(output_path, 'w') as f:
        f.write(rendered_content)
    
    print(f"Successfully rendered {template_path} to {output_path}")

def main():
    parser = argparse.ArgumentParser(description='Render Jinja2 templates with API endpoints')
    parser.add_argument('--template', required=True, help='Path to the template file')
    parser.add_argument('--output', required=True, help='Path for the rendered output')
    parser.add_argument('--search-api', required=True, help='Search API endpoint URL')
    parser.add_argument('--status-api', required=True, help='Status API endpoint URL')
    parser.add_argument('--context-file', help='Optional JSON file with additional context variables')
    
    args = parser.parse_args()
    
    # Build the context dictionary
    context = {
        'search_api_endpoint': args.search_api,
        'status_api_endpoint': args.status_api
    }
    
    # Add additional context from file if provided
    if args.context_file and os.path.exists(args.context_file):
        with open(args.context_file, 'r') as f:
            additional_context = json.load(f)
            context.update(additional_context)
    
    render_template(args.template, args.output, context)

if __name__ == "__main__":
    main()