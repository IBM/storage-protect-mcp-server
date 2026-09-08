import asyncio
import sys
import logging
from dotenv import load_dotenv
from .config import check_env_file_permissions
from .mcp_factory import create_mcp_server, run_server
from .server_groups import (
    ISP_STORAGE_POOLS, ISP_STORAGE_HARDWARE, ISP_STORAGE_DEVICE,
)

# ── CRED-3: check .env permissions before any secrets are loaded ──────────────
check_env_file_permissions()
# Load environment variables from .env file
load_dotenv()


# Configure logging
logger = logging.getLogger("ibm-sp-mcp-server-storage")

async def main():
    logger.info("Starting ISP Storage Server...")
    
    all_storage_commands = ISP_STORAGE_POOLS + ISP_STORAGE_HARDWARE + ISP_STORAGE_DEVICE
    
    server = create_mcp_server("isp-storage", all_storage_commands)
    await run_server(server)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception("Server failed")
        sys.exit(1)
