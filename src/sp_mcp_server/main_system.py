import asyncio
import sys
import logging
from .config import secure_startup
from .mcp_factory import create_mcp_server, run_server
from .server_groups import (
    ISP_SYSTEM_ADMIN, ISP_SYSTEM_CONFIG,
)

# ── CRED-3 / RG-2: permission check and dotenv loading ───────────────────────
secure_startup()

# Configure logging
logger = logging.getLogger("ibm-sp-system")

async def main():
    logger.info("Starting ISP System Server...")
    
    # Combine all system-related commands
    all_system_commands = ISP_SYSTEM_ADMIN + ISP_SYSTEM_CONFIG
    
    server = create_mcp_server("ibm-sp-system", all_system_commands)
    await run_server(server)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception("Server failed")
        sys.exit(1)
