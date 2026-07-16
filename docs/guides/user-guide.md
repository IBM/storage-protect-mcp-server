# User Guide

This guide helps end users get started with the IBM Storage Protect MCP Server after installation. It summarizes what the server does, what you need before using it, how to configure it, and how to interact with it safely.

## What the MCP Server Does

The IBM Storage Protect Model Context Protocol (MCP) server enables natural language administration of IBM Storage Protect environments through AI-assisted workflows. Instead of manually composing every administrative command, you can ask for common operational, configuration, and reporting tasks in plain language.

Typical use cases include:

- checking system status
- reviewing client activity
- investigating failed operations
- querying storage utilization
- assisting with policy and configuration tasks

## Before You Start

Make sure the following are available before using the server:

- an IBM Storage Protect server
- administrator credentials with appropriate permissions
- access to the IBM Storage Protect instance user account when `dsmserv`-based operations are required
- Python 3.10 or higher
- a completed installation of the MCP server

For installation steps, see [`install-guide.md`](install-guide.md) and the main [`README.md`](../../README.md).

## Required Configuration

At minimum, configure these environment variables:

| Variable | Description |
|----------|-------------|
| `SP_ADMIN_ID` | IBM Storage Protect administrator ID |
| `SP_ADMIN_PASSWORD` | IBM Storage Protect administrator password |

Common optional variables:

| Variable | Description |
|----------|-------------|
| `TCPSERVERADDRESS` | Storage Protect server address |
| `SP_SERVER_PORT` or `TCPPORT` | Server port |
| `SP_DSMSERV_PATH` | Path to `dsmserv` |
| `SP_SERVER_INSTANCE_DIR` | Server instance directory |
| `SP_SERVERMON_PATH` | Path to `servermon` |
| `SP_SERVERMON_XML_DIR` | Directory for `servermon` XML output |
| `SP_INSTANCE_USER` | IBM Storage Protect instance user for `dsmserv` commands |

Example:

```bash
export SP_ADMIN_ID=admin
export SP_ADMIN_PASSWORD=mypassword
export TCPSERVERADDRESS=sp-server.example.com
export SP_SERVER_PORT=1500
export SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin/dsmserv
export SP_SERVER_INSTANCE_DIR=/tsminst1
export SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon
export SP_SERVERMON_XML_DIR=/tmp/servermon
export SP_INSTANCE_USER=tsmsvr01
```

## Why `SP_INSTANCE_USER` Matters

Some IBM Storage Protect server-side commands require the correct instance user environment. If `SP_INSTANCE_USER` is not set correctly, `dsmserv` commands can fail because required shared libraries are not loaded in the proper runtime context.

Example error:

```text
/usr/bin/dsmserv: error while loading shared libraries: libdb2.so.1: cannot open shared object file: No such file or directory
```

## Starting the Server

After installation and configuration, activate the virtual environment and start the server.

Example:

```bash
source /opt/sp-mcp-server/venv/bin/activate
python -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage
```

For a more restrictive startup, you can enable only selected server groups or use read-only mode:

```bash
python -m sp_mcp_server.main --mode read-only --enable-servers system,clients
```

## MCP Client Configuration

The MCP server is typically launched by an MCP-compatible client.

Linux example from `README.md`:

```json
{
  "mcpServers": {
    "sp-mcp-server": {
      "command": "sshpass",
      "args": [
        "-p",
        "your_root_password",
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "root@your-sp-server",
        "cd /opt/sp-mcp-server && source venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

For Windows remote access and SSH-based setup, refer to the MCP client configuration section in [`README.md`](../../README.md).

## Example User Requests

Here are some example prompts a user might ask through an MCP client:

```text
What is the database status?
Show me all active clients
Show me all failed operations from the last 24 hours
Create a device class named file_class of type file
Tell me the steps to tier data from container storage pool to cloud storage pool
How many threads are running?
Analyze current capacity utilization and forecast storage exhaustion
```

## Safe Usage Guidance

When using the MCP server in production environments:

- start with read-only queries when validating a new setup
- confirm credentials and target server settings before running administrative actions
- review generated actions carefully before applying changes
- restrict enabled server groups if full administrative scope is not required
- protect `.env` files and credentials with appropriate filesystem permissions

## Basic Validation Checklist

Use this checklist after installation:

1. Verify the package is installed:
   ```bash
   pip list | grep -E "mcp|ibm-sp"
   ```

2. Verify the main command is available:
   ```bash
   which sp-mcp-server
   ```

3. Verify IBM Storage Protect CLI access:
   ```bash
   which dsmadmc
   dsmadmc -id=$SP_ADMIN_ID -password=$SP_ADMIN_PASSWORD "query status"
   ```

4. Start the server in read-only mode:
   ```bash
   python -m sp_mcp_server.main --mode read-only --enable-servers system
   ```

## Related Documentation

- Installation steps: [`install-guide.md`](install-guide.md)
- Main project overview and MCP client setup: [`../../README.md`](../../README.md)
- Build and distribution notes: [`../../build/distribution.md`](../../build/distribution.md)
