"""
Simple proxy server for MCP that adds Bearer token authentication.
Forwards requests to the DataRobot MCP server with authentication.
"""
import argparse
import logging
import os

import dotenv
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import Response
import uvicorn
import httpx

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_proxy_server")

# Load environment variables
dotenv.load_dotenv()

# Target MCP server configuration
MCP_SERVER_URL = os.getenv("MCP_SERVER_URL", "http://localhost:8080")
BEARER_TOKEN = os.getenv("BEARER_TOKEN", "")


async def proxy_handler(request: Request) -> Response:
    """Forward requests to MCP server with Bearer token."""
    try:
        # Get the request body
        body = await request.body()

        # Copy all original headers
        headers = dict(request.headers)

        # Remove host header (will be set by httpx for target)
        headers.pop("host", None)

        # Add/Override Authorization header with Bearer token
        headers["Authorization"] = f"Bearer {BEARER_TOKEN}"

        # Forward the request to the MCP server
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            target_url = f"{MCP_SERVER_URL}{request.url.path}"
            logger.info(f"Forwarding request to: {target_url}")

            response = await client.request(
                method=request.method,
                url=target_url,
                headers=headers,
                content=body,
                params=request.query_params,
            )

            # Copy response headers
            response_headers = dict(response.headers)

            # Remove headers that might cause issues
            response_headers.pop("content-encoding", None)
            response_headers.pop("content-length", None)
            response_headers.pop("transfer-encoding", None)

            # Return the response from MCP server
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers=response_headers,
            )

    except Exception as e:
        logger.error(f"Error proxying request: {e}")
        return Response(
            content=f'{{"error": "Proxy error: {str(e)}"}}',
            status_code=500,
            media_type="application/json",
        )


async def health_check(request: Request) -> Response:
    """Health check endpoint."""
    return Response(
        content='{"status": "healthy", "service": "mcp-proxy-server"}',
        media_type="application/json",
    )


from starlette.routing import Route

# Create Starlette app
app = Starlette(
    debug=True,
    routes=[
        # Health check
        Route("/health", health_check, methods=["GET"]),
        # Proxy all other requests
        Route("/{path:path}", proxy_handler, methods=["GET", "POST", "PUT", "DELETE", "PATCH"]),
    ],
)


def main():
    """Main entry point for proxy server."""
    parser = argparse.ArgumentParser(description="MCP Proxy Server with Bearer Token Authentication")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind to")
    args = parser.parse_args()

    if not BEARER_TOKEN:
        logger.warning("BEARER_TOKEN environment variable is not set!")

    logger.info(f"Starting proxy server on {args.host}:{args.port}")
    logger.info(f"Forwarding to MCP server: {MCP_SERVER_URL}")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
