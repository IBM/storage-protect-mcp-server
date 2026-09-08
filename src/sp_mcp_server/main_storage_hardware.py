import asyncio
import sys
import logging
from .config import secure_startup
from .mcp_factory import create_mcp_server, run_server
from .server_groups import ISP_STORAGE_HARDWARE

# CRED-3 / RG-2: permission check + dotenv in one atomic call
secure_startup()


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("mcp-server-storage-hardware")

async def main():
    server = create_mcp_server("mcp-server-storage-hardware", ISP_STORAGE_HARDWARE)
    await run_server(server)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
