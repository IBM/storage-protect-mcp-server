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
import time
import logging
from dataclasses import dataclass
from threading import RLock
from typing import Optional

logger = logging.getLogger(__name__)

# ── Stream Ownership & Session Context Registry (DAUTH-11 & OA-8) ────────────
@dataclass
class SSESessionContext:
    """OA-8: Active live authorization context for an SSE stream."""
    stream_id: str
    owner_sub: str
    active_privilege: str
    active_exp: float
    active_auth_model: str
    created_at: float
    last_post_at: float


_sse_stream_owners: dict[str, str] = {}
_sse_session_contexts: dict[str, SSESessionContext] = {}
_sse_owners_lock = RLock()


def record_stream_owner(
    session_id: str,
    oidc_subject: str,
    privilege: str = "any",
    exp: float = 0.0,
    auth_model: str = "oidc",
) -> None:
    """DAUTH-11 & OA-8: Register the authenticated OIDC subject and initial session context for an active SSE stream."""
    with _sse_owners_lock:
        sid_str = str(session_id).strip()
        now = time.time()
        _sse_stream_owners[sid_str] = oidc_subject
        ctx = SSESessionContext(
            stream_id=sid_str,
            owner_sub=oidc_subject,
            active_privilege=privilege,
            active_exp=exp,
            active_auth_model=auth_model,
            created_at=now,
            last_post_at=now,
        )
        _sse_session_contexts[sid_str] = ctx
        sid_clean = sid_str.replace("-", "")
        if sid_clean != sid_str:
            _sse_stream_owners[sid_clean] = oidc_subject
            _sse_session_contexts[sid_clean] = ctx


def register_sse_session_context(
    stream_id: str,
    owner_sub: str,
    privilege: str = "any",
    exp: float = 0.0,
    auth_model: str = "oidc",
) -> Optional[SSESessionContext]:
    """OA-8: Register active live authorization context for an SSE stream."""
    record_stream_owner(stream_id, owner_sub, privilege, exp, auth_model)
    return get_sse_session_context(stream_id)


def update_sse_session_context(
    stream_id: str,
    privilege: str,
    exp: float,
    auth_model: str = "oidc",
) -> Optional[SSESessionContext]:
    """OA-8: Dynamically update active privilege and expiration for an active SSE stream from incoming POST claims."""
    with _sse_owners_lock:
        sid_str = str(stream_id).strip()
        ctx = _sse_session_contexts.get(sid_str) or _sse_session_contexts.get(sid_str.replace("-", ""))
        if not ctx and len(sid_str.replace("-", "")) == 32:
            try:
                import uuid
                u_str = str(uuid.UUID(hex=sid_str.replace("-", "")))
                ctx = _sse_session_contexts.get(u_str)
            except Exception:
                pass
        if ctx:
            ctx.active_privilege = privilege
            ctx.active_exp = exp
            ctx.active_auth_model = auth_model
            ctx.last_post_at = time.time()
        return ctx


def get_sse_session_context(session_id: str) -> Optional[SSESessionContext]:
    """OA-8: Retrieve live authorization context for an active SSE stream."""
    with _sse_owners_lock:
        sid_str = str(session_id).strip()
        if sid_str in _sse_session_contexts:
            return _sse_session_contexts[sid_str]
        sid_clean = sid_str.replace("-", "")
        if sid_clean in _sse_session_contexts:
            return _sse_session_contexts[sid_clean]
        if len(sid_clean) == 32:
            try:
                import uuid
                u_str = str(uuid.UUID(hex=sid_clean))
                if u_str in _sse_session_contexts:
                    return _sse_session_contexts[u_str]
            except Exception:
                pass
        return None


def remove_stream_owner(session_id: str) -> None:
    """DAUTH-11 & OA-8: Remove stream ownership mapping and session context when SSE connection disconnects."""
    with _sse_owners_lock:
        sid_str = str(session_id).strip()
        sid_clean = sid_str.replace("-", "")
        _sse_stream_owners.pop(sid_str, None)
        _sse_stream_owners.pop(sid_clean, None)
        _sse_session_contexts.pop(sid_str, None)
        _sse_session_contexts.pop(sid_clean, None)
        if len(sid_clean) == 32:
            try:
                import uuid
                u_str = str(uuid.UUID(hex=sid_clean))
                _sse_stream_owners.pop(u_str, None)
                _sse_session_contexts.pop(u_str, None)
            except Exception:
                pass


def get_stream_owner(session_id: str) -> Optional[str]:
    """DAUTH-11: Retrieve registered OIDC owner for a given stream session ID."""
    with _sse_owners_lock:
        sid_str = str(session_id).strip()
        if sid_str in _sse_stream_owners:
            return _sse_stream_owners[sid_str]
        sid_clean = sid_str.replace("-", "")
        if sid_clean in _sse_stream_owners:
            return _sse_stream_owners[sid_clean]
        if len(sid_clean) == 32:
            try:
                import uuid
                u_str = str(uuid.UUID(hex=sid_clean))
                if u_str in _sse_stream_owners:
                    return _sse_stream_owners[u_str]
            except Exception:
                pass
        return None

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

        token_exp = float(payload.get("exp", 0.0))
        token_sub = payload.get("sub", "unknown")

        scope["user"] = {
            "sub": token_sub,
            "privilege": privilege,
            "exp": token_exp,
            "auth_model": "oidc",
        }
        scope["state"] = scope.get("state", {})
        scope["state"]["mcp_privilege"] = privilege
        scope["state"]["mcp_subject"]   = token_sub
        scope["state"]["mcp_exp"]       = token_exp

        logger.info(
            "INT-2: Authenticated subject='%s' privilege='%s' scopes=%s",
            token_sub, privilege, scopes,
        )

        from .mcp_factory import current_audit_user, current_request_privilege, current_connection_id
        user_ctx = current_audit_user.set(token_sub)
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
        # DAUTH-10 & DAUTH-11 & OA-8: Bind connection identifier and register stream ownership & session context
        caller_sub = request.scope.get("state", {}).get("mcp_subject", "unknown")
        caller_priv = request.scope.get("state", {}).get("mcp_privilege", "any")
        caller_exp = float(request.scope.get("state", {}).get("mcp_exp", 0.0))
        conn_id = request.query_params.get("session_id") or str(id(request))
        token = current_connection_id.set(str(conn_id))

        registered_keys = [str(conn_id)]
        record_stream_owner(str(conn_id), caller_sub, caller_priv, caller_exp)
        before_keys = set(sse_transport._read_stream_writers.keys())

        try:
            async with sse_transport.connect_sse(
                request.scope, request.receive, request._send
            ) as streams:
                new_keys = set(sse_transport._read_stream_writers.keys()) - before_keys
                ctx = get_sse_session_context(str(conn_id))
                for k in new_keys:
                    k_str = str(k)
                    k_hex = k.hex if hasattr(k, "hex") else k_str
                    record_stream_owner(k_str, caller_sub, caller_priv, caller_exp)
                    record_stream_owner(k_hex, caller_sub, caller_priv, caller_exp)
                    registered_keys.extend([k_str, k_hex])
                    if ctx:
                        with _sse_owners_lock:
                            _sse_session_contexts[k_str] = ctx
                            _sse_session_contexts[k_hex] = ctx

                if new_keys:
                    first_k = next(iter(new_keys))
                    current_connection_id.set(str(first_k))

                await mcp_server.run(
                    streams[0],
                    streams[1],
                    mcp_server.create_initialization_options(),
                )
        finally:
            for k in registered_keys:
                remove_stream_owner(k)
            current_connection_id.reset(token)

    async def guarded_post_messages(scope, receive, send):
        """
        DAUTH-11 & OA-8: Guard incoming POST messages to ensure the caller's authenticated OIDC
        identity matches the principal that established the target SSE stream, and update
        the live stream session context with current message privilege and expiration claims.
        """
        if scope["type"] != "http":
            await sse_transport.handle_post_message(scope, receive, send)
            return

        from urllib.parse import parse_qs
        query_bytes = scope.get("query_string", b"")
        target_sid = None
        if query_bytes:
            qs = parse_qs(query_bytes.decode("utf-8", errors="replace"))
            s_list = qs.get("session_id")
            if s_list:
                target_sid = s_list[0]

        caller_sub = scope.get("state", {}).get("mcp_subject", "unknown")
        caller_priv = scope.get("state", {}).get("mcp_privilege", "any")
        caller_exp = float(scope.get("state", {}).get("mcp_exp", 0.0))

        if target_sid:
            owner_sub = get_stream_owner(target_sid)
            if owner_sub is not None and owner_sub != caller_sub:
                logger.warning(
                    "SECURITY (DAUTH-11): Cross-user SSE POST rejected! Caller '%s' "
                    "attempted to post to stream '%s' owned by '%s'.",
                    caller_sub,
                    target_sid,
                    owner_sub,
                )
                response = JSONResponse(
                    {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32001,
                            "message": "Forbidden: stream does not belong to authenticated user.",
                        },
                        "id": None,
                    },
                    status_code=403,
                )
                await response(scope, receive, send)
                return

            # OA-8: Synchronize live session context with incoming POST claims
            update_sse_session_context(
                stream_id=target_sid,
                privilege=caller_priv,
                exp=caller_exp,
                auth_model="oidc",
            )

        await sse_transport.handle_post_message(scope, receive, send)

    async def health(_: Request):
        return JSONResponse({"status": "ok"})

    app = Starlette(
        routes=[
            Route("/health", health),
            Mount(
                "/mcp",
                routes=[
                    Route("/sse",      handle_sse),
                    Mount("/messages", app=guarded_post_messages),
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
