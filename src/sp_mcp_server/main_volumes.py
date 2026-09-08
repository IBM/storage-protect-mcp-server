from __future__ import annotations
import asyncio
from .config import secure_startup
from .mcp_factory import create_mcp_server, run_server
from .server_groups import ISP_VOLUMES

# CRED-3 / RG-2: permission check + dotenv in one atomic call
secure_startup()


def main():
    server = create_mcp_server("isp-volumes", ISP_VOLUMES)
    asyncio.run(run_server(server))

if __name__ == "__main__":
    main()
