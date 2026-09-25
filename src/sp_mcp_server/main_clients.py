from __future__ import annotations
import asyncio
from .config import secure_startup
from .mcp_factory import create_mcp_server, run_server
from .server_groups import ISP_CLIENTS_CORE

# ── CRED-3 / RG-2: permission check and dotenv loading ───────────────────────
secure_startup()


def main():
    server = create_mcp_server("isp-clients", ISP_CLIENTS_CORE)
    asyncio.run(run_server(server))

if __name__ == "__main__":
    main()
