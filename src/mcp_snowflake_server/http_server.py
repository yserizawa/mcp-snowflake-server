"""HTTP wrapper for MCP Snowflake Server for DataRobot deployment."""
import argparse
import asyncio
import json
import logging
import os
from typing import Any

import dotenv
import snowflake.connector
from mcp.server.fastmcp import FastMCP
from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from starlette.routing import Mount, Route
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

# Create FastMCP server for MCP protocol
mcp = FastMCP("snowflake-mcp-server")


# MCP Tools
@mcp.tool()
async def list_databases() -> str:
    """List all available databases in Snowflake"""
    query = "SELECT DATABASE_NAME FROM INFORMATION_SCHEMA.DATABASES"
    data, data_id = await db_client.execute_query(query)
    return json.dumps({"databases": data, "data_id": data_id})


@mcp.tool()
async def list_schemas(database: str) -> str:
    """List all schemas in a database

    Args:
        database: Database name to list schemas from
    """
    query = f"SELECT SCHEMA_NAME FROM {database.upper()}.INFORMATION_SCHEMA.SCHEMATA"
    data, data_id = await db_client.execute_query(query)
    return json.dumps({"database": database, "schemas": data, "data_id": data_id})


@mcp.tool()
async def list_tables(database: str, schema: str) -> str:
    """List all tables in a specific database and schema

    Args:
        database: Database name
        schema: Schema name
    """
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


@mcp.tool()
async def describe_table(table_name: str) -> str:
    """Get the schema information for a specific table

    Args:
        table_name: Fully qualified table name in the format 'database.schema.table'
    """
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


@mcp.tool()
async def read_query(query: str) -> str:
    """Execute a SELECT query

    Args:
        query: SELECT SQL query to execute
    """
    if write_detector.analyze_query(query)["contains_write"]:
        raise ValueError("Calls to read_query should not contain write operations")

    data, data_id = await db_client.execute_query(query)
    return json.dumps({"data": data, "data_id": data_id, "row_count": len(data) if isinstance(data, list) else 0})


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
    global db_client, write_detector

    logger.info("Starting MCP Snowflake HTTP Server")

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
    # Mount MCP Streamable HTTP endpoint
    Mount("/mcp", app=mcp.streamable_http_app()),
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
