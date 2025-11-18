-- Snowflake Network Policy Troubleshooting and Fix
-- Run these commands in Snowflake to resolve the network policy blocking DataRobot IP

-- Step 1: Check current network policies
SHOW NETWORK POLICIES;

-- Step 2: Check which policy is active on the account
SHOW PARAMETERS LIKE 'NETWORK_POLICY' IN ACCOUNT;

-- Step 3: Check which policy is assigned to MCP_USER
SHOW PARAMETERS LIKE 'NETWORK_POLICY' FOR USER MCP_USER;

-- Step 4: Describe the GENERAL policy to see what network rules it includes
DESC NETWORK POLICY GENERAL;

-- Step 5: Describe the SECONDZ policy to see what network rules it includes
DESC NETWORK POLICY SECONDZ;

-- Step 6: Show all network rules to find the DATAROBOT rule
SHOW NETWORK RULES;

-- Step 7: Check the DATAROBOT network rule details
DESC NETWORK RULE "SBCS_DEMO"."INVENTORY_MGMT"."DATAROBOT";

-- ===== SOLUTION OPTIONS =====

-- OPTION 1: Create a new network policy specifically for MCP_USER that includes the DataRobot IPs
-- This is the cleanest solution

CREATE OR REPLACE NETWORK POLICY MCP_USER_POLICY
  ALLOWED_NETWORK_RULE_LIST = ('SBCS_DEMO.INVENTORY_MGMT.DATAROBOT')
  COMMENT = 'Network policy for MCP_USER allowing DataRobot IPs';

-- Apply this policy to MCP_USER
ALTER USER MCP_USER SET NETWORK_POLICY = MCP_USER_POLICY;

-- OPTION 2: Modify the existing GENERAL policy to include the DATAROBOT network rule
-- This affects all users with the GENERAL policy

ALTER NETWORK POLICY GENERAL SET
  ALLOWED_NETWORK_RULE_LIST = (
    -- Add the existing allowed rules here, plus the DATAROBOT rule
    'SBCS_DEMO.INVENTORY_MGMT.DATAROBOT'
    -- Add comma and other existing rules if any
  );

-- OPTION 3: Apply the SECONDZ policy to MCP_USER if it already includes the DataRobot IPs
ALTER USER MCP_USER SET NETWORK_POLICY = SECONDZ;

-- OPTION 4: Temporarily disable network policy for MCP_USER to test
-- (Use only for testing, not recommended for production)
ALTER USER MCP_USER UNSET NETWORK_POLICY;

-- ===== VERIFICATION =====

-- After applying one of the options above, verify the configuration:

-- Check that MCP_USER has the correct policy
SHOW PARAMETERS LIKE 'NETWORK_POLICY' FOR USER MCP_USER;

-- Check the policy details
SHOW NETWORK POLICIES;

-- Describe the policy to see the allowed network rules
DESC NETWORK POLICY MCP_USER_POLICY;  -- Or whichever policy you applied

-- ===== RECOMMENDED APPROACH =====
-- Based on the error and the screenshot, I recommend OPTION 1:
-- 1. Create a dedicated policy for MCP_USER
-- 2. Include only the DATAROBOT network rule
-- 3. This isolates the MCP server from other account-level policies

-- Execute these commands:
CREATE OR REPLACE NETWORK POLICY MCP_USER_POLICY
  ALLOWED_NETWORK_RULE_LIST = ('SBCS_DEMO.INVENTORY_MGMT.DATAROBOT')
  COMMENT = 'Network policy for MCP_USER allowing DataRobot IPs';

ALTER USER MCP_USER SET NETWORK_POLICY = MCP_USER_POLICY;

-- Verify:
SHOW PARAMETERS LIKE 'NETWORK_POLICY' FOR USER MCP_USER;
DESC NETWORK POLICY MCP_USER_POLICY;
