#!/bin/bash
set -e

echo "Starting Snowflake MCP Server deployment..."

# Install dependencies from requirements.txt
echo "Installing dependencies..."
pip install --no-cache-dir -r requirements.txt

# Install the package in editable mode
echo "Installing MCP Snowflake Server package..."
pip install --no-cache-dir -e .

# Start the HTTP server for DataRobot
echo "Starting MCP Snowflake HTTP Server on port 8080..."
exec python -m mcp_snowflake_server.http_server --host 0.0.0.0 --port 8080
