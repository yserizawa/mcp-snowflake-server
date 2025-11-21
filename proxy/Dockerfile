FROM python:3.11-slim

WORKDIR /app

# Install dependencies
RUN pip install --no-cache-dir starlette uvicorn httpx python-dotenv

# Copy proxy server
COPY proxy_server.py /app/

# Expose port
EXPOSE 8000

# Set environment variables (can be overridden at runtime)
ENV MCP_SERVER_URL=http://localhost:8080
ENV BEARER_TOKEN=""

# Run the proxy server
CMD ["python", "/app/proxy_server.py", "--host", "0.0.0.0", "--port", "8000"]
