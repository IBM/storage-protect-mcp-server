import asyncio
import sys
import logging
from .config import secure_startup
from .mcp_factory import create_mcp_server, run_server
from .server_groups import ISP_POLICIES_LIFECYCLE, ISP_POLICIES_MANAGEMENT

# ── CRED-3 / RG-2: permission check and dotenv loading ───────────────────────
secure_startup()

# Configure logging
logger = logging.getLogger("ibm-sp-mcp-server-policy")

async def main():
    logger.info("Starting ISP Policy Server...")

    all_policy_commands = ISP_POLICIES_LIFECYCLE + ISP_POLICIES_MANAGEMENT

    server = create_mcp_server("isp-policy", all_policy_commands)
    await run_server(server)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception("Server failed")
        sys.exit(1)
