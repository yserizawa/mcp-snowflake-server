"""HTTP wrapper for MCP Snowflake Server for DataRobot deployment."""
import argparse
import json
import logging
import os

import dotenv
import snowflake.connector
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Route
import uvicorn

from .db_client import SnowflakeDB
from .write_detector import SQLWriteDetector

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("mcp_snowflake_http_server")

# Global database client
db_client: SnowflakeDB = None
write_detector: SQLWriteDetector = None


def init_db_client():
    """Initialize database client and write detector."""
    global db_client, write_detector

    if db_client is not None:
        return

    logger.info("Initializing database client")

    # Load environment variables
    dotenv.load_dotenv()

    default_connection_args = snowflake.connector.connection.DEFAULT_CONFIGURATION

    connection_args_from_env = {
        k: os.getenv("SNOWFLAKE_" + k.upper())
        for k in default_connection_args
        if os.getenv("SNOWFLAKE_" + k.upper()) is not None
    }

    # Handle token authentication
    snowflake_token = os.getenv("SNOWFLAKE_TOKEN")
    if snowflake_token:
        connection_args_from_env["password"] = snowflake_token

    # Validate required parameters
    if "database" not in connection_args_from_env:
        raise ValueError("SNOWFLAKE_DATABASE environment variable is required")
    if "schema" not in connection_args_from_env:
        raise ValueError("SNOWFLAKE_SCHEMA environment variable is required")

    logger.info(f"Connecting to Snowflake database: {connection_args_from_env.get('database')}")
    logger.info(f"Using schema: {connection_args_from_env.get('schema')}")

    # Initialize database client
    db_client = SnowflakeDB(connection_args_from_env)
    db_client.start_init_connection()

    # Initialize write detector
    write_detector = SQLWriteDetector()

    logger.info("Database connection initialized successfully")


# MCP Tools definition for JSON-RPC endpoint
MCP_TOOLS = [
    {
        "name": "list_databases",
        "description": "List all available databases in Snowflake",
        "inputSchema": {
            "type": "object",
            "properties": {},
        },
    },
    {
        "name": "list_schemas",
        "description": "List all schemas in a database",
        "inputSchema": {
            "type": "object",
            "properties": {
                "database": {
                    "type": "string",
                    "description": "Database name to list schemas from",
                },
            },
            "required": ["database"],
        },
    },
    {
        "name": "list_tables",
        "description": "List all tables in a specific database and schema",
        "inputSchema": {
            "type": "object",
            "properties": {
                "database": {"type": "string", "description": "Database name"},
                "schema": {"type": "string", "description": "Schema name"},
            },
            "required": ["database", "schema"],
        },
    },
    {
        "name": "describe_table",
        "description": "Get the schema information for a specific table",
        "inputSchema": {
            "type": "object",
            "properties": {
                "table_name": {
                    "type": "string",
                    "description": "Fully qualified table name in the format 'database.schema.table'",
                },
            },
            "required": ["table_name"],
        },
    },
    {
        "name": "read_query",
        "description": "Execute a SELECT query",
        "inputSchema": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "SELECT SQL query to execute"},
            },
            "required": ["query"],
        },
    },
]


async def mcp_endpoint(request: Request) -> Response:
    """MCP JSON-RPC endpoint for Streamable HTTP transport."""
    try:
        init_db_client()
        data = await request.json()

        jsonrpc = data.get("jsonrpc", "2.0")
        method = data.get("method")
        params = data.get("params", {})
        request_id = data.get("id")

        result = None
        error = None

        if method == "initialize":
            result = {
                "protocolVersion": "2024-11-05",
                "capabilities": {
                    "tools": {"listChanged": False},
                },
                "serverInfo": {
                    "name": "snowflake-mcp-server",
                    "version": "0.4.0",
                },
            }

        elif method == "tools/list":
            result = {"tools": MCP_TOOLS}

        elif method == "tools/call":
            tool_name = params.get("name")
            arguments = params.get("arguments", {})

            try:
                tool_result = await execute_mcp_tool(tool_name, arguments)
                result = {
                    "content": [
                        {"type": "text", "text": tool_result}
                    ]
                }
            except Exception as e:
                result = {
                    "content": [
                        {"type": "text", "text": f"Error: {str(e)}"}
                    ],
                    "isError": True
                }

        elif method == "notifications/initialized":
            # This is a notification, no response needed
            return Response(status_code=204)

        else:
            error = {
                "code": -32601,
                "message": f"Method not found: {method}"
            }

        response_data = {"jsonrpc": jsonrpc, "id": request_id}
        if error:
            response_data["error"] = error
        else:
            response_data["result"] = result

        return JSONResponse(response_data)

    except Exception as e:
        logger.error(f"Error in MCP endpoint: {e}")
        return JSONResponse({
            "jsonrpc": "2.0",
            "id": None,
            "error": {
                "code": -32603,
                "message": str(e)
            }
        }, status_code=500)


async def execute_mcp_tool(tool_name: str, arguments: dict) -> str:
    """Execute an MCP tool and return the result as JSON string."""
    if tool_name == "list_databases":
        query = "SELECT DATABASE_NAME FROM INFORMATION_SCHEMA.DATABASES"
        data, data_id = await db_client.execute_query(query)
        return json.dumps({"databases": data, "data_id": data_id})

    elif tool_name == "list_schemas":
        database = arguments.get("database")
        if not database:
            raise ValueError("Missing required 'database' parameter")
        query = f"SELECT SCHEMA_NAME FROM {database.upper()}.INFORMATION_SCHEMA.SCHEMATA"
        data, data_id = await db_client.execute_query(query)
        return json.dumps({"database": database, "schemas": data, "data_id": data_id})

    elif tool_name == "list_tables":
        database = arguments.get("database")
        schema = arguments.get("schema")
        if not database or not schema:
            raise ValueError("Missing required 'database' and 'schema' parameters")
        query = f"""
            SELECT table_catalog, table_schema, table_name, comment
            FROM {database}.information_schema.tables
            WHERE table_schema = '{schema.upper()}'
        """
        data, data_id = await db_client.execute_query(query)
        return json.dumps({
            "database": database,
            "schema": schema,
            "tables": data,
            "data_id": data_id
        })

    elif tool_name == "describe_table":
        table_name = arguments.get("table_name")
        if not table_name:
            raise ValueError("Missing required 'table_name' parameter")

        split_identifier = table_name.split(".")
        if len(split_identifier) < 3:
            raise ValueError("Table name must be fully qualified as 'database.schema.table'")

        database_name = split_identifier[0].upper()
        schema_name = split_identifier[1].upper()
        tbl_name = split_identifier[2].upper()

        query = f"""
            SELECT column_name, column_default, is_nullable, data_type, comment
            FROM {database_name}.information_schema.columns
            WHERE table_schema = '{schema_name}' AND table_name = '{tbl_name}'
        """
        data, data_id = await db_client.execute_query(query)
        return json.dumps({
            "database": database_name,
            "schema": schema_name,
            "table": tbl_name,
            "columns": data,
            "data_id": data_id
        })

    elif tool_name == "read_query":
        query = arguments.get("query")
        if not query:
            raise ValueError("Missing required 'query' parameter")

        if write_detector.analyze_query(query)["contains_write"]:
            raise ValueError("Calls to read_query should not contain write operations")

        data, data_id = await db_client.execute_query(query)
        return json.dumps({
            "data": data,
            "data_id": data_id,
            "row_count": len(data) if isinstance(data, list) else 0
        })

    else:
        raise ValueError(f"Unknown tool: {tool_name}")


async def health_check(request: Request) -> Response:
    """Health check endpoint for DataRobot."""
    return JSONResponse({"status": "healthy", "service": "mcp-snowflake-server"})


async def execute_query_endpoint(request: Request) -> Response:
    """Execute a SQL query endpoint."""
    try:
        data = await request.json()
        query = data.get("query")

        if not query:
            return JSONResponse(
                {"error": "Missing 'query' parameter"},
                status_code=400
            )

        # Execute query
        results, data_id = await db_client.execute_query(query)

        return JSONResponse({
            "data": results,
            "data_id": data_id,
            "row_count": len(results) if isinstance(results, list) else 0
        })

    except Exception as e:
        logger.error(f"Error executing query: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


async def list_databases_endpoint(request: Request) -> Response:
    """List all databases."""
    try:
        query = "SELECT DATABASE_NAME FROM INFORMATION_SCHEMA.DATABASES"
        results, data_id = await db_client.execute_query(query)

        return JSONResponse({
            "databases": results,
            "data_id": data_id
        })

    except Exception as e:
        logger.error(f"Error listing databases: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


async def list_schemas_endpoint(request: Request) -> Response:
    """List schemas in a database."""
    try:
        database = request.query_params.get("database")

        if not database:
            return JSONResponse(
                {"error": "Missing 'database' parameter"},
                status_code=400
            )

        query = f"SELECT SCHEMA_NAME FROM {database.upper()}.INFORMATION_SCHEMA.SCHEMATA"
        results, data_id = await db_client.execute_query(query)

        return JSONResponse({
            "database": database,
            "schemas": results,
            "data_id": data_id
        })

    except Exception as e:
        logger.error(f"Error listing schemas: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


async def list_tables_endpoint(request: Request) -> Response:
    """List tables in a schema."""
    try:
        database = request.query_params.get("database")
        schema = request.query_params.get("schema")

        if not database or not schema:
            return JSONResponse(
                {"error": "Missing 'database' or 'schema' parameter"},
                status_code=400
            )

        query = f"""
            SELECT table_catalog, table_schema, table_name, comment
            FROM {database}.information_schema.tables
            WHERE table_schema = '{schema.upper()}'
        """
        results, data_id = await db_client.execute_query(query)

        return JSONResponse({
            "database": database,
            "schema": schema,
            "tables": results,
            "data_id": data_id
        })

    except Exception as e:
        logger.error(f"Error listing tables: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


async def describe_table_endpoint(request: Request) -> Response:
    """Describe a table schema."""
    try:
        table_name = request.query_params.get("table")

        if not table_name:
            return JSONResponse(
                {"error": "Missing 'table' parameter (format: database.schema.table)"},
                status_code=400
            )

        split_identifier = table_name.split(".")
        if len(split_identifier) < 3:
            return JSONResponse(
                {"error": "Table name must be fully qualified as 'database.schema.table'"},
                status_code=400
            )

        database_name = split_identifier[0].upper()
        schema_name = split_identifier[1].upper()
        table_name = split_identifier[2].upper()

        query = f"""
            SELECT column_name, column_default, is_nullable, data_type, comment
            FROM {database_name}.information_schema.columns
            WHERE table_schema = '{schema_name}' AND table_name = '{table_name}'
        """
        results, data_id = await db_client.execute_query(query)

        return JSONResponse({
            "database": database_name,
            "schema": schema_name,
            "table": table_name,
            "columns": results,
            "data_id": data_id
        })

    except Exception as e:
        logger.error(f"Error describing table: {e}")
        return JSONResponse(
            {"error": str(e)},
            status_code=500
        )


async def startup():
    """Initialize database connection on startup."""
    logger.info("Starting MCP Snowflake HTTP Server")
    init_db_client()


async def shutdown():
    """Cleanup on shutdown."""
    global db_client
    logger.info("Shutting down server")
    if db_client:
        # Close database connections if needed
        pass


# Define routes
routes = [
    Route("/", health_check, methods=["GET"]),
    Route("/health", health_check, methods=["GET"]),
    Route("/api/query", execute_query_endpoint, methods=["POST"]),
    Route("/api/databases", list_databases_endpoint, methods=["GET"]),
    Route("/api/schemas", list_schemas_endpoint, methods=["GET"]),
    Route("/api/tables", list_tables_endpoint, methods=["GET"]),
    Route("/api/table/describe", describe_table_endpoint, methods=["GET"]),
    # MCP JSON-RPC endpoint for Streamable HTTP transport
    Route("/mcp", mcp_endpoint, methods=["POST"]),
]

# Create Starlette app
app = Starlette(
    debug=True,
    routes=routes,
    on_startup=[startup],
    on_shutdown=[shutdown],
)


def main():
    """Main entry point for HTTP server."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")
    parser.add_argument("--port", type=int, default=8080, help="Port to bind to")
    args = parser.parse_args()

    logger.info(f"Starting server on {args.host}:{args.port}")

    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        log_level="info",
    )


if __name__ == "__main__":
    main()
