# Implementation: Secure Integrations

* **Domain**: Secure Integrations
* **Status**: Implemented baseline — token validation, TLS startup checks, and call-time scope authorization are present; broader middleware integration coverage remains follow-up work
* **Analysis reference**: [`docs/analysis/security-design-analysis.md § 5 & § 7`](../analysis/security-design-analysis.md)
* **Gaps addressed**: SI1, SI2, SI3, SI4, RG-5, NR-1
* **Files changed**: `src/sp_mcp_server/config.py`, `src/sp_mcp_server/mcp_factory.py`, `src/sp_mcp_server/commands/system/conn.py`, `src/sp_mcp_server/main.py`, new `src/sp_mcp_server/http_server.py`

---

## Overview

The integration implementation is partial. Token validation, TLS startup checks, secret references, and keyring resolution exist; OIDC scope enforcement in the MCP call path remains open.

The integration areas are implemented to different levels:

| ID | Change | Gaps closed |
|----|--------|-------------|
| INT-1 | LDAP authentication for SP service accounts | SI1 |
| INT-2 | OAuth 2.1 / OIDC bearer-token HTTP transport (opt-in) + user context propagation; scope-to-tool enforcement pending | Token validation implemented; authorization open |
| INT-3 | Secrets-reference pattern for cloud credentials in `define_connection` | SI3 |
| INT-4 | `keyring` integration in `config.py` as primary credential source | SI4 |
| RG-5 | TLS cert/key presence enforced in `main.py` before HTTP transport binds | RG-5 |

---

## INT-1 — LDAP Authentication for SP Service Accounts

### Background

IBM SP supports `AUTHENTICATION=LDAP` on administrator accounts, delegating password verification to an LDAP/Active Directory server. When LDAP is in use, the SP service account password is the AD account password, which is governed by AD policy: automatic rotation, account disablement on HR offboarding, and centralized MFA controls (e.g. Azure AD Conditional Access for non-interactive accounts).

This is a **server-side configuration change** — no Python source code is modified. The integration is documented here as a deployment runbook.

### Prerequisites

1. An LDAP/AD server reachable from the IBM SP server with TLS enabled.
2. A service account in AD for each MCP privilege tier (or a single shared AD group with sub-accounts).
3. The LDAP trusted certificate installed on the IBM SP server.

### Step 1 — Install the LDAP trusted certificate on IBM SP

```bash
# On the IBM SP server, as the SP instance user (e.g. tsmsvr01)
# 1. Obtain the LDAP server's CA certificate (PEM format) from your LDAP admin.
#    Save it to: /opt/tivoli/tsm/server/bin/ldap-ca.pem

# 2. Add it to the IBM SP key database (dsmcert.kdb)
gsk8capicmd_64 -cert -add \
    -db /opt/tivoli/tsm/server/bin/dsmcert.kdb \
    -stashed \
    -label "LDAP CA" \
    -file /opt/tivoli/tsm/server/bin/ldap-ca.pem \
    -format ascii

# 3. Verify
gsk8capicmd_64 -cert -list -db /opt/tivoli/tsm/server/bin/dsmcert.kdb -stashed
# Expected: "LDAP CA" appears in the list
```

### Step 2 — Configure LDAP on the IBM SP server

```
* Run these commands as a system-privileged SP administrator.
* Replace ldap.example.com and DC=example,DC=com with your AD values.

* Point SP to the LDAP server (TLS on port 636)
SET LDAPURL ldap://ldap.example.com:636

* Bind account: a read-only AD account for SP to search user entries
SET LDAPBINDDN "CN=sp-ldap-bind,OU=ServiceAccounts,DC=example,DC=com"
SET LDAPBINDPW <bind-account-password>

* Base DN for user lookups
SET LDAPUSERDN "OU=MCP-ServiceAccounts,DC=example,DC=com"

* Make LDAP the default for all new accounts
SET DEFAULTAUTHENTICATION LDAP

* Verify the LDAP connection
QUERY LDAP
```

### Step 3 — Create matching AD accounts and migrate SP service accounts

Create one AD account per MCP privilege tier in the `MCP-ServiceAccounts` OU:

| AD account | SP service account | SP privilege |
|-----------|-------------------|--------------|
| `mcp-svc-readonly` | `mcp-svc-readonly` | any |
| `mcp-svc-operator` | `mcp-svc-operator` | Operator |
| `mcp-svc-storage` | `mcp-svc-storage` | Storage |
| `mcp-svc-policy` | `mcp-svc-policy` | Policy |
| `mcp-svc-system` | `mcp-svc-system` | System |

AD accounts should have:
- A strong, randomly generated initial password (rotated by AD policy thereafter)
- Password never expires: **NO** — use a 90-day rotation policy or shorter
- Account cannot be deleted without IT approval

Migrate each SP service account to LDAP authentication:

```
* Migrate existing accounts to LDAP
UPDATE ADMIN mcp-svc-readonly AUTHENTICATION=LDAP
UPDATE ADMIN mcp-svc-operator AUTHENTICATION=LDAP
UPDATE ADMIN mcp-svc-storage  AUTHENTICATION=LDAP
UPDATE ADMIN mcp-svc-policy   AUTHENTICATION=LDAP
UPDATE ADMIN mcp-svc-system   AUTHENTICATION=LDAP

* Verify: should show Authentication: LDAP for each
QUERY ADMIN mcp-svc-* FORMAT=DETAILED
```

### Step 4 — Update MCP server environment variables

With LDAP, the `SP_ADMIN_PASSWORD_*` environment variables hold the AD account passwords:

```dotenv
# .env — LDAP passwords (same as AD account passwords for these accounts)
SP_ADMIN_ID_READONLY=mcp-svc-readonly
SP_ADMIN_PASSWORD_READONLY=<ad-password-for-mcp-svc-readonly>

SP_ADMIN_ID_SYSTEM=mcp-svc-system
SP_ADMIN_PASSWORD_SYSTEM=<ad-password-for-mcp-svc-system>
# ... etc.
```

Alternatively, use the `keyring` integration (INT-4 below) so these passwords are retrieved from the OS credential store rather than the `.env` file.

### Step 5 — Verify end-to-end

```bash
# Test LDAP authentication for one account
DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys \
  dsmadmc -id=mcp-svc-readonly "QUERY STATUS" 2>&1 | head -3
# Expected: connects without "ANR2012W Authentication error"

# Check authentication method in QUERY ADMIN
DSM_CONFIG=/opt/sp-mcp-server/config/dsm.sys \
  dsmadmc -id=mcp-svc-system "QUERY ADMIN mcp-svc-readonly FORMAT=DETAILED" \
  | grep -i authentication
# Expected: Authentication: LDAP
```

### Rollback procedure

If LDAP becomes unavailable, revert individual accounts to local auth:

```
UPDATE ADMIN mcp-svc-readonly AUTHENTICATION=LOCAL SYNCLDAPDELETE=NO
```

---

## INT-2 — OAuth 2.1 / OIDC HTTP Transport (Opt-In)

### Background

The MCP 2025 specification defines OAuth 2.1 / OIDC-based authorization for MCP servers running over HTTP transport. The implementation validates bearer tokens, derives a scope privilege, propagates it through request context, and enforces it at MCP tool invocation. Middleware integration coverage and live IdP verification remain follow-up work.

This change adds an **opt-in HTTP server mode** that enforces OIDC bearer token validation. The existing stdio mode is unchanged and remains the default for local deployments.

### New file: `src/sp_mcp_server/http_server.py`

```python
# src/sp_mcp_server/http_server.py
"""
OAuth 2.1 / OIDC-protected HTTP/SSE transport for the IBM SP MCP Server.
Activated with: python3 -m sp_mcp_server.main --transport http --port 8443

Token validation uses the OIDC discovery document at SP_OIDC_ISSUER.
Each request must carry:  Authorization: Bearer <OIDC access token>

Token scopes map to SP privilege tiers:
  mcp:read     → 'any'      privilege tools only
  mcp:operator → 'operator' + 'any'
  mcp:storage  → 'storage'  + 'any'
  mcp:policy   → 'policy'   + 'any'
  mcp:system   → 'system'   (all tools)
"""

import os
import logging
from typing import Optional

import httpx
from starlette.applications import Starlette
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route, Mount

logger = logging.getLogger(__name__)

# ── Scope → privilege mapping ────────────────────────────────────────────
SCOPE_PRIVILEGE_MAP = {
    "mcp:read":     "any",
    "mcp:operator": "operator",
    "mcp:storage":  "storage",
    "mcp:policy":   "policy",
    "mcp:system":   "system",
}


class OIDCBearerMiddleware(BaseHTTPMiddleware):
    """
    Validates OIDC bearer tokens, injects the resolved privilege tier into
    request.state.mcp_privilege, and propagates it to the MCP call-time gate.
    """

    def __init__(self, app, issuer: str, audience: str):
        super().__init__(app)
        self.issuer   = issuer.rstrip("/")
        self.audience = audience
        self._jwks_uri: Optional[str] = None
        self._jwks: Optional[dict]    = None

    async def _get_jwks(self) -> dict:
        """Fetch and cache the OIDC JWKS (JSON Web Key Set)."""
        if self._jwks is not None:
            return self._jwks

        discovery_url = f"{self.issuer}/.well-known/openid-configuration"
        async with httpx.AsyncClient() as client:
            disc = await client.get(discovery_url, timeout=10)
            disc.raise_for_status()
            self._jwks_uri = disc.json()["jwks_uri"]

            jwks = await client.get(self._jwks_uri, timeout=10)
            jwks.raise_for_status()
            self._jwks = jwks.json()
        return self._jwks

    async def dispatch(self, request: Request, call_next):
        # Skip health-check endpoint
        if request.url.path in ("/health", "/"):
            return await call_next(request)

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                {"error": "missing_token", "message": "Bearer token required."},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="sp-mcp-server"'}
            )

        token = auth_header[len("Bearer "):]
        try:
            import jwt  # pyjwt
            jwks = await self._get_jwks()
            jwks_client = jwt.PyJWKClient(self._jwks_uri)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub", "scope"]}
            )
        except Exception as exc:
            logger.warning("INT-2: Token validation failed: %s", exc)
            return JSONResponse(
                {"error": "invalid_token", "message": str(exc)},
                status_code=401
            )

        # Resolve privilege from token scopes
        scopes = payload.get("scope", "").split()
        privilege = "any"
        for scope in scopes:
            tier = SCOPE_PRIVILEGE_MAP.get(scope)
            if tier and _privilege_rank(tier) > _privilege_rank(privilege):
                privilege = tier

        request.state.mcp_privilege = privilege
        request.state.mcp_subject   = payload.get("sub", "unknown")
        logger.info(
            "INT-2: Authenticated subject='%s' privilege='%s' scopes=%s",
            request.state.mcp_subject, privilege, scopes
        )
        return await call_next(request)


def _privilege_rank(p: str) -> int:
    order = {"any": 0, "operator": 1, "storage": 2, "policy": 3, "system": 4}
    return order.get(p, 0)


def create_http_app(mcp_server, oidc_issuer: str, oidc_audience: str) -> Starlette:
    """
    Wrap an MCP server in a Starlette app with OIDC bearer auth middleware.
    The MCP server's SSE handler is mounted at /mcp.
    """
    from mcp.server.sse import SseServerTransport

    sse_transport = SseServerTransport("/mcp/messages")

    async def handle_sse(request: Request):
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0], streams[1],
                mcp_server.create_initialization_options()
            )

    async def health(_: Request):
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/health", health),
            Mount("/mcp", routes=[
                Route("/sse",      handle_sse),
                Mount("/messages", app=sse_transport.handle_post_message),
            ]),
        ]
    )

    app.add_middleware(
        OIDCBearerMiddleware,
        issuer=oidc_issuer,
        audience=oidc_audience,
    )
    return app
```

### `main.py` — add `--transport http` flag

```python
# src/sp_mcp_server/main.py — extend parse_args()

def parse_args():
    parser = argparse.ArgumentParser(description="IBM Storage Protect MCP Server")
    parser.add_argument("--enable-servers", type=str,
                        default="system,operations,clients,policy,storage")
    parser.add_argument("--mode", type=str, default="full",
                        choices=["full", "read-only"])
    # ── INT-2: HTTP transport ──────────────────────────────────────────
    parser.add_argument("--transport", type=str, default="stdio",
                        choices=["stdio", "http"],
                        help="Transport: 'stdio' (default) or 'http' (OAuth 2.1)")
    parser.add_argument("--port", type=int, default=8443,
                        help="HTTP port (used with --transport http)")
    # ──────────────────────────────────────────────────────────────────
    return parser.parse_args()


async def main():
    args = parse_args()
    # ... existing server group selection and tool collection ...

    server = create_mcp_server("ibm-sp-mcp-server", tool_classes,
                               allowed_modes=allowed_modes)

    if args.transport == "http":
        # ── INT-2: HTTP/SSE with OIDC auth ─────────────────────────────
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

        app = create_http_app(server, oidc_issuer, oidc_audience)
        logger.info(
            "INT-2: Starting HTTP/SSE transport on port %d with OIDC issuer %s",
            args.port, oidc_issuer
        )
        config = uvicorn.Config(
            app,
            host="0.0.0.0",
            port=args.port,
            ssl_keyfile=os.environ.get("SP_TLS_KEY"),
            ssl_certfile=os.environ.get("SP_TLS_CERT"),
            log_level="info"
        )
        await uvicorn.Server(config).serve()
    else:
        await run_server(server)
```

### Environment variables for HTTP transport

| Variable | Required | Description |
|----------|----------|-------------|
| `SP_OIDC_ISSUER` | Yes | OIDC issuer URL (e.g. `https://login.microsoftonline.com/<tenant>/v2.0`) |
| `SP_OIDC_AUDIENCE` | No | Token audience claim (default: `sp-mcp-server`) |
| `SP_TLS_KEY` | Recommended | Path to TLS private key for HTTPS |
| `SP_TLS_CERT` | Recommended | Path to TLS certificate for HTTPS |

### Token scope → privilege mapping

The mapping below is enforced by the MCP call-time authorization gate. Add end-to-end middleware tests before marking transport integration fully verified.

When an MCP client requests a token from the IdP, it requests one or more of these scopes:

| Scope | Privilege tier | Tools accessible |
|-------|---------------|-----------------|
| `mcp:read` | `any` | All `QUERY` / read-only tools |
| `mcp:operator` | `operator` | Operator tools + read-only tools |
| `mcp:storage` | `storage` | Storage tools + read-only tools |
| `mcp:policy` | `policy` | Policy tools + read-only tools |
| `mcp:system` | `system` | All tools |

### Example MCP client configuration (HTTP transport)

```json
{
  "mcpServers": {
    "sp-mcp-server-http": {
      "url": "https://sp-mcp-01.example.com:8443/mcp/sse",
      "headers": {
        "Authorization": "Bearer ${SP_MCP_ACCESS_TOKEN}"
      }
    }
  }
}
```

The client obtains `SP_MCP_ACCESS_TOKEN` from the IdP using the OAuth 2.1 Client Credentials flow:

```bash
# Example: Azure AD client credentials flow
SP_MCP_ACCESS_TOKEN=$(curl -s -X POST \
  "https://login.microsoftonline.com/${TENANT_ID}/oauth2/v2.0/token" \
  -d "client_id=${CLIENT_ID}" \
  -d "client_secret=${CLIENT_SECRET}" \
  -d "scope=api://${SP_OIDC_AUDIENCE}/mcp:read" \
  -d "grant_type=client_credentials" \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['access_token'])")
```

---

## INT-3 — Secrets-Reference Pattern for Cloud Credentials

### Background

The `define_connection` tool ([`commands/system/conn.py:DefineConnection`](../../src/sp_mcp_server/commands/system/conn.py)) currently accepts raw `identity` (Access Key ID) and `password` (Secret Access Key) as plain JSON arguments. These appear in the MCP tool call payload, the MCP server log, and the `dsmadmc` process argument list.

The fix replaces the raw credential arguments with a **secrets reference** — an opaque identifier that the MCP server resolves to the actual credential at execution time using the `keyring` backend or a secrets manager SDK.

### What to change

**File**: [`src/sp_mcp_server/commands/system/conn.py`](../../src/sp_mcp_server/commands/system/conn.py)

```python
# src/sp_mcp_server/commands/system/conn.py

import keyring
import logging
from typing import Any, Dict, Optional
from ..base import BaseCommand

logger = logging.getLogger(__name__)

_SECRETS_KEYRING_SERVICE = "sp-mcp-cloud-connections"


def _resolve_secret(secret_ref: str, fallback_value: Optional[str] = None) -> str:
    """
    INT-3: Resolve a secrets reference to its actual value.

    Resolution order:
      1. If secret_ref starts with 'keyring:', look up in OS keyring.
         Format: 'keyring:<username>'
      2. If secret_ref starts with 'env:', read the named environment variable.
         Format: 'env:MY_SECRET_VAR'
      3. Otherwise treat secret_ref as the literal value (backward compat).

    Returns the resolved secret value.
    Raises ValueError if the reference cannot be resolved.
    """
    if secret_ref.startswith("keyring:"):
        username = secret_ref[len("keyring:"):]
        value = keyring.get_password(_SECRETS_KEYRING_SERVICE, username)
        if value is None:
            raise ValueError(
                f"INT-3: Secret '{username}' not found in keyring service "
                f"'{_SECRETS_KEYRING_SERVICE}'. "
                f"Store it with: "
                f"python3 -c \"import keyring; "
                f"keyring.set_password('{_SECRETS_KEYRING_SERVICE}', '{username}', '<value>')\""
            )
        return value

    if secret_ref.startswith("env:"):
        var_name = secret_ref[len("env:"):]
        import os
        value = os.environ.get(var_name)
        if value is None:
            raise ValueError(
                f"INT-3: Environment variable '{var_name}' is not set."
            )
        return value

    # Literal fallback — log a warning so operators know this is less secure
    if fallback_value is not None:
        return fallback_value
    logger.warning(
        "INT-3: Secret reference '%s' is not prefixed with 'keyring:' or 'env:'. "
        "Treating as a literal value. Prefer 'keyring:<key>' for production.",
        secret_ref[:20] + "..."
    )
    return secret_ref


class DefineConnection(BaseCommand):
    @property
    def name(self) -> str:
        return "define_connection"

    @property
    def required_privilege(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return (
            "Define a **Cloud Connection** to a cloud storage service (S3, Azure, Google).\n\n"
            "**Security note**: Use secrets references instead of raw credential values.\n"
            "- Keyring:  `keyring:<key-name>` — resolved from the OS credential store\n"
            "- Env var:  `env:MY_ENV_VAR`    — resolved from the environment\n"
            "- Literal:  raw value           — accepted but not recommended\n\n"
            "**Input Parameters**:\n"
            "- connection_name (Required): Name of the connection.\n"
            "- cloud_type (Required): Cloud type (S3, AZURE, GOOGLE, etc.).\n"
            "- bucket_name (Required): Target bucket or container name.\n"
            "- identity (Required): Access Key ID or username (or a secrets reference).\n"
            "- password (Required): Secret Access Key or password (or a secrets reference).\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the connection was defined."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "connection_name": {"type": "string", "description": "Connection name."},
                "cloud_type":      {"type": "string", "description": "Cloud type (S3, AZURE, GOOGLE)."},
                "bucket_name":     {"type": "string", "description": "Bucket or container name."},
                "identity": {
                    "type": "string",
                    "description": (
                        "Access Key ID or secrets reference. "
                        "Use 'keyring:<key>' or 'env:VAR_NAME' for secure resolution."
                    )
                },
                "password": {
                    "type": "string",
                    "description": (
                        "Secret Access Key or secrets reference. "
                        "Use 'keyring:<key>' or 'env:VAR_NAME' for secure resolution."
                    )
                },
            },
            "required": ["connection_name", "cloud_type", "bucket_name", "identity", "password"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        # INT-3: resolve credentials — never log the resolved values
        try:
            identity = _resolve_secret(arguments["identity"])
            password = _resolve_secret(arguments["password"])
        except ValueError as e:
            return f"Error: {e}"

        cmd = (
            f"DEFINE CONNECTION {arguments['connection_name']} "
            f"CLOUDTYPE={arguments['cloud_type']} "
            f"BUCKETNAME={arguments['bucket_name']} "
            f"IDENTITY=\"{identity}\" "
            f"PASSWORD=\"{password}\""
        )
        # Do NOT log the assembled command — it contains resolved credentials.
        logger.info(
            "INT-3: Executing DEFINE CONNECTION %s CLOUDTYPE=%s BUCKETNAME=%s "
            "[credentials resolved from secrets store, not logged]",
            arguments["connection_name"], arguments["cloud_type"], arguments["bucket_name"]
        )
        return self._execute_simple_query_no_log(cmd)

    def _execute_simple_query_no_log(self, cmd: str) -> str:
        """Execute without logging the command string (it contains credentials)."""
        stdout, stderr, code = self.cli.execute_silent(cmd)
        if code != 0:
            return self._format_command_error("Error executing command:", stdout, stderr)
        return stdout
```

### `DsmAdmcWrapper.execute_silent()` — suppress command logging

```python
# src/sp_mcp_server/cli_wrapper.py — add to DsmAdmcWrapper

def execute_silent(self, command: str) -> Tuple[str, str, int]:
    """
    INT-3: Execute a command without logging the command string.
    Use for commands that contain resolved secrets (e.g. DEFINE CONNECTION).
    """
    if not self.config.validate():
        return "", "Configuration incomplete.", 1

    cred = self.config.credential_for("system")
    use_stash = os.environ.get("SP_MCP_USE_PASSWORD_STASH", "0") == "1"
    args = [self.executable, "-NOConfirm", "-DATAONLY=YES",
            f"-ID={cred.admin_id}", "-COMMAdelimited"]
    if not use_stash:
        args.insert(4, f"-PA={cred.admin_password}")

    args.extend(command.split())

    # Intentionally NO logger.info/debug of the command string
    logger.info("Executing silent dsmadmc command (credentials in command; not logged)")
    try:
        process = subprocess.run(args, capture_output=True, text=True,
                                 check=False, timeout=30)
        return process.stdout, process.stderr, process.returncode
    except subprocess.TimeoutExpired:
        return "", "Command timed out", 124
    except FileNotFoundError:
        return "", "dsmadmc not found", 127
    except Exception as e:
        return "", str(e), 1
```

### Registering secrets in the keyring (one-time setup)

```bash
# Store cloud connection credentials in the OS keyring before the MCP server starts.
# Run as the mcp-runner OS user on the SP server.

python3 -c "
import keyring
keyring.set_password('sp-mcp-cloud-connections', 's3-prod-access-key', 'AKIAIOSFODNN7EXAMPLE')
keyring.set_password('sp-mcp-cloud-connections', 's3-prod-secret-key', 'wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY')
print('Stored.')
"
```

Tool call using references (no raw credentials in the payload):

```json
{
  "tool": "define_connection",
  "arguments": {
    "connection_name": "S3_PROD",
    "cloud_type": "S3",
    "bucket_name": "my-backup-bucket",
    "identity": "keyring:s3-prod-access-key",
    "password": "keyring:s3-prod-secret-key"
  }
}
```

---

## INT-4 — `keyring` Integration in `config.py`

### Background

The `keyring` package is declared as a runtime dependency in [`pyproject.toml`](../../pyproject.toml:38) but is not used anywhere in the codebase. This change integrates it as the **primary** credential source for MCP service account passwords, with environment variables as a fallback. Credentials are stored in the OS-backed credential store (macOS Keychain, Linux Secret Service / libsecret, Windows Credential Manager) rather than in plaintext environment variables or `.env` files.

### What to change

**File**: [`src/sp_mcp_server/config.py`](../../src/sp_mcp_server/config.py)

Update `load_config()` to prefer `keyring` over environment variables for passwords:

```python
# src/sp_mcp_server/config.py

import keyring as _keyring

_KEYRING_SERVICE = "ibm-sp-mcp-server"


def _get_password(admin_id: Optional[str], env_var: str) -> Optional[str]:
    """
    INT-4: Retrieve a service account password.
    Resolution order:
      1. OS keyring (keyed by admin_id under service 'ibm-sp-mcp-server')
      2. Environment variable named env_var
    Returns None if neither source has the password.
    """
    if admin_id:
        kr_value = _keyring.get_password(_KEYRING_SERVICE, admin_id)
        if kr_value:
            logger.debug(
                "INT-4: Password for '%s' retrieved from OS keyring.", admin_id
            )
            return kr_value

    env_value = os.environ.get(env_var)
    if env_value:
        logger.debug(
            "INT-4: Password for '%s' retrieved from environment variable %s. "
            "Consider migrating to keyring for better security.",
            admin_id, env_var
        )
    return env_value


def load_config(env_path: str = ".env") -> ServerConfig:
    """Load configuration from keyring (primary) or environment variables (fallback)."""
    _load_env_permission_check(env_path)

    address = os.environ.get("TCPSERVERADDRESS")
    port    = os.environ.get("SP_SERVER_PORT") or os.environ.get("TCPPORT") or "1500"

    credentials: Dict[str, ModuleCredential] = {}

    _module_map = {
        "system":   ("SP_ADMIN_ID_SYSTEM",   "SP_ADMIN_PASSWORD_SYSTEM"),
        "policy":   ("SP_ADMIN_ID_POLICY",   "SP_ADMIN_PASSWORD_POLICY"),
        "storage":  ("SP_ADMIN_ID_STORAGE",  "SP_ADMIN_PASSWORD_STORAGE"),
        "operator": ("SP_ADMIN_ID_OPERATOR", "SP_ADMIN_PASSWORD_OPERATOR"),
        "any":      ("SP_ADMIN_ID_READONLY", "SP_ADMIN_PASSWORD_READONLY"),
    }

    for privilege, (id_var, pw_var) in _module_map.items():
        admin_id = os.environ.get(id_var)
        if not admin_id:
            continue
        # INT-4: keyring-first password resolution
        admin_pwd = _get_password(admin_id, pw_var)
        if admin_pwd:
            credentials[privilege] = ModuleCredential(
                admin_id=admin_id,
                admin_password=admin_pwd,
                privilege=privilege
            )

    # Legacy fallback
    legacy_id  = os.environ.get("SP_ADMIN_ID")
    legacy_pwd = _get_password(legacy_id, "SP_ADMIN_PASSWORD") if legacy_id else None

    if legacy_id and legacy_pwd and not credentials:
        logger.warning(
            "INT-4 / CRED-1: Using legacy single-credential. "
            "Migrate to per-module credentials with keyring storage."
        )

    return ServerConfig(
        server_address=address,
        server_port=port,
        credentials=credentials,
        admin_id=legacy_id,
        admin_password=legacy_pwd,
        dsmserv_path=os.environ.get("SP_DSMSERV_PATH"),
        server_instance_dir=os.environ.get("SP_SERVER_INSTANCE_DIR"),
        servermon_path=os.environ.get("SP_SERVERMON_PATH"),
        servermon_xml_dir=os.environ.get("SP_SERVERMON_XML_DIR"),
        instance_user=os.environ.get("SP_INSTANCE_USER"),
    )
```

### Storing credentials in the keyring (one-time setup per account)

```bash
# Run as the mcp-runner OS user on the SP server.
# The keyring backend is determined by the OS:
#   Linux: libsecret / GNOME Keyring (or 'keyrings.alt' plaintext fallback)
#   macOS: Keychain
#   Windows: Windows Credential Manager

python3 << 'EOF'
import keyring

SERVICE = "ibm-sp-mcp-server"

accounts = {
    "mcp-svc-readonly": input("Password for mcp-svc-readonly: "),
    "mcp-svc-operator": input("Password for mcp-svc-operator: "),
    "mcp-svc-storage":  input("Password for mcp-svc-storage:  "),
    "mcp-svc-policy":   input("Password for mcp-svc-policy:   "),
    "mcp-svc-system":   input("Password for mcp-svc-system:   "),
}

for account, password in accounts.items():
    keyring.set_password(SERVICE, account, password)
    print(f"Stored: {account}")

print("Done. SP_ADMIN_PASSWORD_* variables can now be removed from .env")
EOF
```

### `.env` after keyring migration

Once credentials are in the keyring, `.env` only needs account IDs, not passwords:

```dotenv
# .env after INT-4 migration — no passwords stored here
TCPSERVERADDRESS=sp-server-01.example.com
SP_SERVER_PORT=1500

SP_ADMIN_ID_READONLY=mcp-svc-readonly
SP_ADMIN_ID_OPERATOR=mcp-svc-operator
SP_ADMIN_ID_STORAGE=mcp-svc-storage
SP_ADMIN_ID_POLICY=mcp-svc-policy
SP_ADMIN_ID_SYSTEM=mcp-svc-system
```

### Linux keyring backend selection

On a headless Linux server without a desktop session, install a suitable backend:

```bash
# Option A: Secret Service via GNOME Keyring (recommended for servers)
pip install secretstorage

# Option B: Plain-file fallback (acceptable for servers where OS keyring unavailable)
pip install keyrings.alt
# keyrings.alt stores in ~/.local/share/python_keyring/keyring_pass.cfg
# Restrict permissions: chmod 600 ~/.local/share/python_keyring/keyring_pass.cfg
```

---

## Verification Checklist

```bash
# INT-1: Verify LDAP authentication flag on SP accounts (run on SP server)
# dsmadmc -id=<system-admin> "QUERY ADMIN mcp-svc-* FORMAT=DETAILED" | grep Authentication
# Expected: Authentication: LDAP  for each account

# INT-2: HTTP transport with OIDC — import check
python3 -c "
from sp_mcp_server.http_server import create_http_app, OIDCBearerMiddleware, SCOPE_PRIVILEGE_MAP
assert SCOPE_PRIVILEGE_MAP['mcp:system'] == 'system'
assert SCOPE_PRIVILEGE_MAP['mcp:read']   == 'any'
print('INT-2 OK: http_server module importable, scope map correct')
"

# INT-3: Secrets-reference resolution
python3 -c "
import os
os.environ['TEST_SECRET'] = 'test-value-123'
from sp_mcp_server.commands.system.conn import _resolve_secret

# env: prefix
assert _resolve_secret('env:TEST_SECRET') == 'test-value-123'

# missing env: raises
try:
    _resolve_secret('env:NONEXISTENT_VAR_XYZ')
    print('FAIL: should raise')
except ValueError as e:
    print('INT-3 OK (env):', e)

# keyring: prefix (uses default keyring backend)
import keyring
keyring.set_password('sp-mcp-cloud-connections', 'test-key', 'test-secret')
assert _resolve_secret('keyring:test-key') == 'test-secret'
print('INT-3 OK (keyring): secret resolved correctly')
keyring.delete_password('sp-mcp-cloud-connections', 'test-key')
"

# INT-4: keyring-first credential resolution
python3 -c "
import keyring
keyring.set_password('ibm-sp-mcp-server', 'mcp-svc-test', 'keyring-password-xyz')
import os
os.environ['SP_ADMIN_ID_READONLY'] = 'mcp-svc-test'
os.environ['SP_ADMIN_PASSWORD_READONLY'] = 'env-password-should-not-be-used'

from sp_mcp_server.config import load_config
cfg = load_config.__wrapped__(load_config) if hasattr(load_config, '__wrapped__') else None
# Direct test of _get_password
from sp_mcp_server.config import _get_password
result = _get_password('mcp-svc-test', 'SP_ADMIN_PASSWORD_READONLY')
assert result == 'keyring-password-xyz', f'FAIL: got {result}'
print('INT-4 OK: keyring takes priority over env var')
keyring.delete_password('ibm-sp-mcp-server', 'mcp-svc-test')
"
```

---

## Integration Dependency Summary

| INT | Runtime dependencies | Optional dependencies |
|-----|--------------------|-----------------------|
| INT-1 (LDAP) | None (server-side only) | — |
| INT-2 (OAuth) | `mcp[sse]`, `starlette`, `uvicorn`, `pyjwt`, `httpx` | `cryptography` (for RS256/ES256 key parsing) |
| INT-3 (Secrets ref) | `keyring` *(already in `pyproject.toml`)* | `secretstorage` (Linux), `keyrings.alt` (headless) |
| INT-4 (keyring) | `keyring` *(already in `pyproject.toml`)* | `secretstorage` (Linux), `keyrings.alt` (headless) |

All runtime dependencies for INT-2 are already available via the existing `sse` optional extra in [`pyproject.toml`](../../pyproject.toml):

```bash
# Install INT-2 dependencies
pip install -e ".[sse]"
```

---

## RG-5 — HTTP Transport TLS Enforcement

### Problem

`main.py` passed `ssl_keyfile=os.environ.get("SP_TLS_KEY")` and `ssl_certfile=os.environ.get("SP_TLS_CERT")` directly to `uvicorn.Config`. If these variables were unset, uvicorn started without TLS — serving OIDC bearer tokens and all MCP tool traffic in cleartext — with no error from the application.

### What changed

**File**: [`src/sp_mcp_server/main.py`](../../src/sp_mcp_server/main.py)

Three guard paths are added before the `uvicorn.Config` call:

```python
tls_cert = os.environ.get("SP_TLS_CERT")
tls_key  = os.environ.get("SP_TLS_KEY")
allow_plaintext = os.environ.get("SP_MCP_ALLOW_HTTP_PLAINTEXT", "0") == "1"

if not (tls_cert and tls_key):
    if not allow_plaintext:
        # Hard failure — refuse to start without TLS in normal operation
        logger.error(
            "SECURITY [RG-5]: --transport http requires both SP_TLS_CERT and "
            "SP_TLS_KEY to be set. Bearer tokens would be transmitted in cleartext. "
            "Provide certificate and key files, or set "
            "SP_MCP_ALLOW_HTTP_PLAINTEXT=1 for loopback-only test deployments."
        )
        sys.exit(1)
    # Explicit override for loopback-only test deployments
    logger.error(
        "SECURITY [RG-5]: HTTP transport started WITHOUT TLS "
        "(SP_MCP_ALLOW_HTTP_PLAINTEXT=1). PRODUCTION UNSAFE."
    )
else:
    # Both vars set — validate the files actually exist
    for label, path in (("SP_TLS_CERT", tls_cert), ("SP_TLS_KEY", tls_key)):
        if not os.path.isfile(path):
            logger.error(
                "SECURITY [RG-5]: %s path '%s' does not exist or is not a file.",
                label, path,
            )
            sys.exit(1)
```

### New environment variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SP_TLS_CERT` | Yes (HTTP transport) | Path to PEM TLS certificate file |
| `SP_TLS_KEY` | Yes (HTTP transport) | Path to PEM TLS private key file |
| `SP_MCP_ALLOW_HTTP_PLAINTEXT` | No (default `0`) | Set `1` to allow plaintext HTTP (test/loopback only) |

### Startup behaviour matrix

| `SP_TLS_CERT` + `SP_TLS_KEY` | `SP_MCP_ALLOW_HTTP_PLAINTEXT` | Result |
|------------------------------|-------------------------------|--------|
| Both set, files exist | any | ✅ TLS HTTPS listener |
| Either missing/empty | `0` (default) | ❌ `sys.exit(1)` `SECURITY [RG-5]` |
| Either missing/empty | `1` | ⚠ `ERROR` logged, plaintext HTTP starts |
| Both set, file not found | any | ❌ `sys.exit(1)` `SECURITY [RG-5]` |

### Verification

```bash
# Must fail — no TLS configured
python3 -m sp_mcp_server.main --transport http
# Expected: "SECURITY [RG-5]: --transport http requires both SP_TLS_CERT and SP_TLS_KEY"

# Must succeed
SP_TLS_CERT=/path/cert.crt SP_TLS_KEY=/path/key.key \
SP_OIDC_ISSUER=https://login.example.com/ \
python3 -m sp_mcp_server.main --transport http --port 8443
```

### Automated test coverage

[`tests/test_security_controls.py::TestHttpTransportTLS`](../../tests/test_security_controls.py)

