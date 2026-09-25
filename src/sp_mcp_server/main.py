import asyncio
import os
import sys
import logging
import argparse

# ── CRED-3 / RG-2: permission check + dotenv in one atomic call ───────────────
from .config import secure_startup
secure_startup()
# ─────────────────────────────────────────────────────────────────────────────

from .mcp_factory import create_mcp_server, run_server
from .server_groups import (
    ISP_CLIENTS_CORE, ISP_CLIENTS_CONFIG,
    ISP_STORAGE_POOLS, ISP_STORAGE_HARDWARE, ISP_STORAGE_DEVICE,
    ISP_POLICIES_LIFECYCLE, ISP_POLICIES_MANAGEMENT,
    ISP_SYSTEM_ADMIN, ISP_SYSTEM_CONFIG,
    ISP_OPS_PROTECTION, ISP_OPS_MAINTENANCE, ISP_OPS_RULES
)

# Configure logging
logger = logging.getLogger("ibm-sp-mcp-server")

# Define Server Group Mappings
# Define Server Group Mappings
SERVER_GROUPS = {
    # System & Security
    "system": ISP_SYSTEM_ADMIN + ISP_SYSTEM_CONFIG,
    
    # Operations
    "operations": ISP_OPS_PROTECTION + ISP_OPS_MAINTENANCE + ISP_OPS_RULES,
    
    # Clients
    "clients": ISP_CLIENTS_CORE + ISP_CLIENTS_CONFIG,
    
    # Policy
    "policy": ISP_POLICIES_LIFECYCLE + ISP_POLICIES_MANAGEMENT,
    
    # Storage
    "storage": ISP_STORAGE_POOLS + ISP_STORAGE_HARDWARE + ISP_STORAGE_DEVICE
}

def parse_args():
    parser = argparse.ArgumentParser(description="IBM Storage Protect MCP Server")
    parser.add_argument(
        "--enable-servers",
        type=str,
        default="system,operations,clients,policy,storage",
        help="Comma-separated list of server modules to enable (default: all)"
    )
    parser.add_argument(
        "--mode",
        type=str,
        default="full",
        choices=["full", "read-only"],
        help="Operation mode: 'full' (all commands) or 'read-only' (query/info only)"
    )
    # ── INT-2: HTTP/SSE transport with OIDC bearer auth ───────────────────────
    parser.add_argument(
        "--transport",
        type=str,
        default="stdio",
        choices=["stdio", "http"],
        help="Transport: 'stdio' (default, local) or 'http' (OAuth 2.1 / OIDC bearer tokens)",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8443,
        help="HTTP port (used with --transport http, default: 8443)",
    )
    # ─────────────────────────────────────────────────────────────────────────
    return parser.parse_args()

async def main():
    args = parse_args()
    
    # Determine enabled servers
    enabled_servers = [s.strip() for s in args.enable_servers.split(",") if s.strip()]
    
    # Collect tools
    tool_classes = []
    for server_key in enabled_servers:
        if server_key in SERVER_GROUPS:
            logger.info(f"Enabling server module: {server_key}")
            tool_classes.extend(SERVER_GROUPS[server_key])
        else:
            logger.warning(f"Unknown server module: {server_key}")
            
    if not tool_classes:
        logger.error("No valid server modules enabled. Exiting.")
        sys.exit(1)

    # Determine allowed modes
    allowed_modes = ["read-only"] if args.mode == "read-only" else ["full"]
    logger.info(f"Starting server in {args.mode} mode")

    server = create_mcp_server("ibm-sp-mcp-server", tool_classes, allowed_modes=allowed_modes)

    if args.transport == "http":
        # ── INT-2: HTTP/SSE transport with OIDC bearer auth ───────────────────
        import uvicorn
        from .http_server import create_http_app

        oidc_issuer   = os.environ.get("SP_OIDC_ISSUER")
        oidc_audience = os.environ.get("SP_OIDC_AUDIENCE", "sp-mcp-server")

        if not oidc_issuer:
            logger.error(
                "INT-2: --transport http requires SP_OIDC_ISSUER environment variable. "
                "Example: SP_OIDC_ISSUER=https://login.microsoftonline.com/<tenant>/v2.0"
            )
            sys.exit(1)

        # ── RG-5: enforce TLS certificate presence before binding ─────────────
        tls_cert = os.environ.get("SP_TLS_CERT")
        tls_key  = os.environ.get("SP_TLS_KEY")
        allow_plaintext = os.environ.get("SP_MCP_ALLOW_HTTP_PLAINTEXT", "0") == "1"

        if not (tls_cert and tls_key):
            if not allow_plaintext:
                logger.error(
                    "SECURITY [RG-5]: --transport http requires both SP_TLS_CERT and "
                    "SP_TLS_KEY to be set. "
                    "Bearer tokens and MCP traffic would be transmitted in cleartext "
                    "without TLS. "
                    "Provide certificate and key files, or set "
                    "SP_MCP_ALLOW_HTTP_PLAINTEXT=1 for loopback-only test deployments."
                )
                sys.exit(1)
            logger.error(
                "SECURITY [RG-5]: HTTP transport started WITHOUT TLS "
                "(SP_MCP_ALLOW_HTTP_PLAINTEXT=1). "
                "PRODUCTION UNSAFE — bearer tokens transmitted in cleartext. "
                "Do not use this in production."
            )
        else:
            # Validate files actually exist before handing to uvicorn
            for label, path in (("SP_TLS_CERT", tls_cert), ("SP_TLS_KEY", tls_key)):
                if not os.path.isfile(path):
                    logger.error(
                        "SECURITY [RG-5]: %s path '%s' does not exist or is not a file.",
                        label, path,
                    )
                    sys.exit(1)
        # ─────────────────────────────────────────────────────────────────────

        app = create_http_app(server, oidc_issuer, oidc_audience)
        logger.info(
            "INT-2: Starting HTTP/SSE transport on port %d with OIDC issuer %s",
            args.port, oidc_issuer,
        )
        uvicorn_config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=args.port,
            ssl_keyfile=tls_key,
            ssl_certfile=tls_cert,
            log_level="info",
        )
        await uvicorn.Server(uvicorn_config).serve()
    else:
        await run_server(server)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logger.exception("Server failed")
        sys.exit(1)
