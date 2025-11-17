#!/bin/bash
set -e

echo "Starting Snowflake MCP Server deployment..."

# Install dependencies from requirements.txt
echo "Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# Install the package in editable mode
echo "Installing MCP Snowflake Server package..."
pip install --no-cache-dir -e .

# Start the MCP server
echo "Starting MCP Snowflake Server..."
exec mcp_snowflake_server
