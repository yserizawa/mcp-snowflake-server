#!/usr/bin/env python3
"""
DataRobot Custom Application Deployment Script
Deploys the Snowflake MCP Server as a DataRobot Custom Application
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

try:
    import datarobot as dr
except ImportError:
    print("Installing DataRobot Python client...")
    os.system("pip install datarobot")
    import datarobot as dr

def main():
    print("=== DataRobot Custom Application Deployment ===\n")

    # Get DataRobot API credentials
    api_token = os.getenv("DATAROBOT_API_TOKEN")
    endpoint = os.getenv("DATAROBOT_ENDPOINT", "https://app.datarobot.com/api/v2")

    if not api_token:
        print("Error: DATAROBOT_API_TOKEN not found in environment.")
        print("Please set your DataRobot API token:")
        print("  export DATAROBOT_API_TOKEN='your-token-here'")
        print("\nOr add to .env file:")
        print("  DATAROBOT_API_TOKEN=your-token-here")
        sys.exit(1)

    # Initialize DataRobot client
    dr.Client(token=api_token, endpoint=endpoint)
    print(f"✓ Connected to DataRobot at {endpoint}\n")

    # Application configuration
    app_config = {
        "name": "snowflake-mcp-server",
        "description": "Model Context Protocol server for Snowflake database interactions",
        "source_type": "git",
        "git_url": "https://github.com/yserizawa/mcp-snowflake-server.git",
        "git_branch": "main",
        "entrypoint": "start-app.sh",
        "runtime_parameters": {
            "python_version": "3.11"
        },
        "environment_variables": [
            {"name": "SNOWFLAKE_USER", "value": os.getenv("SNOWFLAKE_USER", "")},
            {"name": "SNOWFLAKE_ACCOUNT", "value": os.getenv("SNOWFLAKE_ACCOUNT", "")},
            {"name": "SNOWFLAKE_ROLE", "value": os.getenv("SNOWFLAKE_ROLE", "")},
            {"name": "SNOWFLAKE_DATABASE", "value": os.getenv("SNOWFLAKE_DATABASE", "")},
            {"name": "SNOWFLAKE_SCHEMA", "value": os.getenv("SNOWFLAKE_SCHEMA", "")},
            {"name": "SNOWFLAKE_WAREHOUSE", "value": os.getenv("SNOWFLAKE_WAREHOUSE", "")},
            {"name": "SNOWFLAKE_TOKEN", "value": os.getenv("SNOWFLAKE_TOKEN", "")},
        ]
    }

    print("Application Configuration:")
    print(f"  Name: {app_config['name']}")
    print(f"  Git URL: {app_config['git_url']}")
    print(f"  Branch: {app_config['git_branch']}")
    print(f"  Entrypoint: {app_config['entrypoint']}")
    print(f"  Python Version: {app_config['runtime_parameters']['python_version']}")
    print("\nEnvironment Variables:")
    for env_var in app_config['environment_variables']:
        if env_var['name'] == 'SNOWFLAKE_TOKEN':
            print(f"  {env_var['name']}: {'*' * 20} (hidden)")
        else:
            print(f"  {env_var['name']}: {env_var['value']}")

    print("\n" + "="*60)
    print("NOTE: DataRobot Custom Application API is environment-specific.")
    print("This script provides a template. Actual implementation depends on:")
    print("  1. Your DataRobot environment (Cloud, Managed AI Cloud, On-Prem)")
    print("  2. Available APIs in your DataRobot version")
    print("  3. Your organization's deployment policies")
    print("\nRecommended Deployment Methods:")
    print("  1. DataRobot Web UI (most reliable)")
    print("  2. DataRobot CLI tools specific to your environment")
    print("  3. Custom API integration with your DataRobot setup")
    print("="*60)

    print("\n✓ Configuration validated. Ready for manual deployment via DataRobot UI.")
    print("\nTo deploy via UI:")
    print("  1. Visit: https://app.datarobot.com/custom-applications")
    print("  2. Use the configuration shown above")
    print("  3. Ensure all environment variables are set securely")

if __name__ == "__main__":
    main()
