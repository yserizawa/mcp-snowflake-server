#!/bin/bash
set -e

echo "Installing dependencies..."
pip install --no-cache-dir starlette uvicorn httpx python-dotenv

echo "Starting proxy server..."
python /app/proxy_server.py --host 0.0.0.0 --port 8000
