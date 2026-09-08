from __future__ import annotations
import asyncio
from dotenv import load_dotenv
from .config import check_env_file_permissions
from .mcp_factory import create_mcp_server, run_server
from .server_groups import ISP_STORAGE_DEVICE

# ── CRED-3: check .env permissions before any secrets are loaded ──────────────
check_env_file_permissions()
# Load environment variables from .env file
load_dotenv()


def main():
    server = create_mcp_server("isp-devclass", ISP_STORAGE_DEVICE)
    asyncio.run(run_server(server))

if __name__ == "__main__":
    main()
