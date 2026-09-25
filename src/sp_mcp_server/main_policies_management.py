import asyncio
import sys
import logging
from .config import secure_startup
from .mcp_factory import create_mcp_server, run_server
from .server_groups import ISP_POLICIES_MANAGEMENT

# CRED-3 / RG-2: permission check + dotenv in one atomic call
secure_startup()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server-policies-management")

async def main():
    server = create_mcp_server("mcp-server-policies-management", ISP_POLICIES_MANAGEMENT)
    await run_server(server)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
