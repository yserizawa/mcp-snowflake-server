#!/bin/bash
set -e

echo "=== DataRobot Deployment Script for Snowflake MCP Server ==="

# Check if DataRobot CLI is installed
if ! command -v datarobot &> /dev/null; then
    echo "Installing DataRobot CLI..."
    pip install datarobot
fi

# Load environment variables from .env
if [ -f .env ]; then
    echo "Loading environment variables from .env..."
    export $(cat .env | grep -v '^#' | xargs)
else
    echo "Warning: .env file not found. Please ensure environment variables are set."
fi

# DataRobot deployment configuration
APP_NAME="snowflake-mcp-server"
DESCRIPTION="Model Context Protocol server for Snowflake database interactions"

echo ""
echo "Deployment Configuration:"
echo "  App Name: ${APP_NAME}"
echo "  Description: ${DESCRIPTION}"
echo "  Source Path: $(pwd)"
echo ""

# Note: This script provides the structure for DataRobot deployment
# The actual deployment commands will depend on your DataRobot setup

cat <<EOF

Next Steps for DataRobot Deployment:
=====================================

Option 1: Deploy via DataRobot Web UI
--------------------------------------
1. Log in to DataRobot: https://app.datarobot.com
2. Navigate to: Applications → Custom Applications
3. Click: "Create Application"
4. Configure:
   - Name: ${APP_NAME}
   - Source: Git Repository
   - Repository URL: https://github.com/yserizawa/mcp-snowflake-server
   - Branch: main
   - Entrypoint: start-app.sh
5. Set Environment Variables:
   - SNOWFLAKE_USER: ${SNOWFLAKE_USER}
   - SNOWFLAKE_ACCOUNT: ${SNOWFLAKE_ACCOUNT}
   - SNOWFLAKE_ROLE: ${SNOWFLAKE_ROLE}
   - SNOWFLAKE_DATABASE: ${SNOWFLAKE_DATABASE}
   - SNOWFLAKE_SCHEMA: ${SNOWFLAKE_SCHEMA}
   - SNOWFLAKE_WAREHOUSE: ${SNOWFLAKE_WAREHOUSE}
   - SNOWFLAKE_TOKEN: [Enter token securely via UI]
6. Click: "Deploy"

Option 2: Deploy via DataRobot API (Python)
--------------------------------------------
Run the Python deployment script:
  python deploy-datarobot-api.py

Option 3: Deploy from CodeSpaces
---------------------------------
If deploying from DataRobot CodeSpaces:
1. Navigate to your CodeSpace
2. Clone/Update the repository:
   cd /home/notebooks/storage
   git clone https://github.com/yserizawa/mcp-snowflake-server.git
   # or: cd mcp-snowflake-server && git pull

3. Create application via DataRobot UI pointing to CodeSpaces path:
   /home/notebooks/storage/mcp-snowflake-server

EOF

echo ""
echo "Would you like to generate a Python API deployment script? (requires DataRobot API token)"
