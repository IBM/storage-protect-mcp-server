"""
OAuth 2.1 / OIDC-protected HTTP/SSE transport for the IBM SP MCP Server.

Activated with:
    python3 -m sp_mcp_server.main --transport http --port 8443

Token validation uses the OIDC discovery document at SP_OIDC_ISSUER.
Each request must carry:  Authorization: Bearer <OIDC access token>

Token scopes map to SP privilege tiers:
    mcp:read     → 'any'      (read-only query tools)
    mcp:operator → 'operator' + 'any'
    mcp:storage  → 'storage'  + 'any'
    mcp:policy   → 'policy'   + 'any'
    mcp:system   → 'system'   (all tools)

References:
    - docs/implement/impl-security-integrations.md § INT-2
    - docs/design/security-integrations.md
"""

import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── Scope → privilege mapping ─────────────────────────────────────────────────
SCOPE_PRIVILEGE_MAP = {
    "mcp:read":     "any",
    "mcp:operator": "operator",
    "mcp:storage":  "storage",
    "mcp:policy":   "policy",
    "mcp:system":   "system",
}


def _privilege_rank(p: str) -> int:
    order = {"any": 0, "operator": 1, "storage": 2, "policy": 3, "system": 4}
    return order.get(p, 0)


class OIDCBearerMiddleware:
    """
    INT-2: ASGI middleware that validates OIDC bearer tokens on every incoming
    HTTP request and injects the resolved privilege tier into request.state.

    Compatible with Starlette's BaseHTTPMiddleware interface.
    """

    def __init__(self, app, issuer: str, audience: str):
        self.app      = app
        self.issuer   = issuer.rstrip("/")
        self.audience = audience
        self._jwks_uri: Optional[str] = None
        self._jwks: Optional[dict]    = None

    async def _get_jwks(self) -> dict:
        """Fetch and cache the OIDC JWKS (JSON Web Key Set)."""
        if self._jwks is not None:
            return self._jwks

        import httpx
        discovery_url = f"{self.issuer}/.well-known/openid-configuration"
        async with httpx.AsyncClient() as client:
            disc = await client.get(discovery_url, timeout=10)
            disc.raise_for_status()
            jwks_uri: str = disc.json()["jwks_uri"]
            self._jwks_uri = jwks_uri

            jwks = await client.get(jwks_uri, timeout=10)
            jwks.raise_for_status()
            self._jwks = jwks.json()
        assert self._jwks is not None
        return self._jwks

    async def __call__(self, scope, receive, send):
        from starlette.requests import Request
        from starlette.responses import JSONResponse

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)

        # Skip health-check endpoint
        if request.url.path in ("/health", "/"):
            await self.app(scope, receive, send)
            return

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            response = JSONResponse(
                {"error": "missing_token", "message": "Bearer token required."},
                status_code=401,
                headers={"WWW-Authenticate": 'Bearer realm="sp-mcp-server"'},
            )
            await response(scope, receive, send)
            return

        token = auth_header[len("Bearer "):]
        try:
            import jwt  # pyjwt
            await self._get_jwks()
            if self._jwks_uri is None:
                raise RuntimeError("JWKS URI could not be resolved from OIDC discovery document.")
            jwks_client = jwt.PyJWKClient(self._jwks_uri)
            signing_key = jwks_client.get_signing_key_from_jwt(token)

            payload = jwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub", "scope"]},
            )
        except Exception as exc:
            logger.warning("INT-2: Token validation failed: %s", exc)
            response = JSONResponse(
                {"error": "invalid_token", "message": str(exc)},
                status_code=401,
            )
            await response(scope, receive, send)
            return

        # Resolve privilege from token scopes (highest wins)
        scopes = payload.get("scope", "").split()
        privilege = "any"
        for scope_claim in scopes:
            tier = SCOPE_PRIVILEGE_MAP.get(scope_claim)
            if tier and _privilege_rank(tier) > _privilege_rank(privilege):
                privilege = tier

        scope["state"] = scope.get("state", {})
        scope["state"]["mcp_privilege"] = privilege
        scope["state"]["mcp_subject"]   = payload.get("sub", "unknown")

        logger.info(
            "INT-2: Authenticated subject='%s' privilege='%s' scopes=%s",
            scope["state"]["mcp_subject"], privilege, scopes,
        )

        from .mcp_factory import current_audit_user, current_request_privilege, current_connection_id
        user_ctx = current_audit_user.set(scope["state"]["mcp_subject"])
        privilege_ctx = current_request_privilege.set(privilege)

        # DAUTH-10: Extract transport connection ID from query parameters if present
        conn_id = None
        query_bytes = scope.get("query_string", b"")
        if query_bytes:
            from urllib.parse import parse_qs
            qs = parse_qs(query_bytes.decode("utf-8", errors="replace"))
            conn_vals = qs.get("session_id")
            if conn_vals:
                conn_id = conn_vals[0]
        conn_ctx = current_connection_id.set(str(conn_id)) if conn_id else None

        try:
            await self.app(scope, receive, send)
        finally:
            if conn_ctx:
                current_connection_id.reset(conn_ctx)
            current_request_privilege.reset(privilege_ctx)
            current_audit_user.reset(user_ctx)


def create_http_app(mcp_server, oidc_issuer: str, oidc_audience: str):
    """
    INT-2: Wrap an MCP server in a Starlette app with OIDC bearer auth middleware.
    The MCP server's SSE handler is mounted at /mcp.
    Note: SseServerTransport uses relative "messages" endpoint to correctly
    advertise "/mcp/messages" under the "/mcp" mount (DAUTH-10).

    Returns a Starlette ASGI application.
    """
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from mcp.server.sse import SseServerTransport
    from .mcp_factory import current_connection_id

    sse_transport = SseServerTransport("messages")

    async def handle_sse(request: Request):
        # DAUTH-10: Bind connection identifier into context for per-stream session isolation
        conn_id = request.query_params.get("session_id") or str(id(request))
        token = current_connection_id.set(str(conn_id))
        try:
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                await mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp_server.create_initialization_options(),
                )
        finally:
            current_connection_id.reset(token)

    async def health(_: Request):
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/health", health),
            Mount(
                "/mcp",
                routes=[
                    Route("/sse",      handle_sse),
                    Mount("/messages", app=sse_transport.handle_post_message),
                ],
            ),
        ]
    )

    app.add_middleware(
        OIDCBearerMiddleware,
        issuer=oidc_issuer,
        audience=oidc_audience,
    )
    return app
