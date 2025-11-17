#!/bin/bash
set -e

echo "Starting Snowflake MCP Server deployment..."

# Install uv if not available
if ! command -v uv &> /dev/null; then
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Install dependencies with compatible versions
echo "Installing dependencies..."
pip install --upgrade pyOpenSSL>=24.0.0 cryptography>=41.0.0

# Sync uv dependencies
echo "Syncing uv dependencies..."
uv sync

# Start the MCP server
echo "Starting MCP Snowflake Server..."
exec uv run mcp_snowflake_server
