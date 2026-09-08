import asyncio
import sys
import logging
from .config import secure_startup
from .mcp_factory import create_mcp_server, run_server
from .server_groups import (
    ISP_LOGS, ISP_JOBS, ISP_ALERTS,
    ISP_BACKUPSET, ISP_CATALOG, ISP_DATA_MOVEMENT,
    ISP_DR, ISP_FILESYSTEM, ISP_MEDIA,
    ISP_REPLICATION, ISP_RULES, ISP_MISC_OPS
)

# CRED-3 / RG-2: permission check + dotenv in one atomic call
secure_startup()

# Configure logging
logger = logging.getLogger("ibm-sp-mcp-server-ops")

async def main():
    logger.info("Starting ISP Operations Server...")
    
    # Combine all operation-related commands
    all_ops_commands = (
        ISP_LOGS + ISP_JOBS + ISP_ALERTS +
        ISP_BACKUPSET + ISP_CATALOG + ISP_DATA_MOVEMENT +
        ISP_DR + ISP_FILESYSTEM + ISP_MEDIA +
        ISP_REPLICATION + ISP_RULES + ISP_MISC_OPS
    )
    
    server = create_mcp_server("isp-ops", all_ops_commands)
    await run_server(server)

def main_sync():
    """Synchronous entry point for the MCP server"""
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception("Server failed")
        sys.exit(1)

if __name__ == "__main__":
    main_sync()
