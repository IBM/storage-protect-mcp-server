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
    - docs/implement/impl-security-oauth2.md (OA-1 through OA-7)
    - docs/design/security-oauth2.md
"""

import os
import logging
import time
from typing import Optional

import httpx

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


# ── OA-1: AS metadata cache ───────────────────────────────────────────────────
_as_metadata_cache: Optional[dict] = None
_as_metadata_fetched_at: float = 0.0
_AS_METADATA_TTL: float = 3600.0  # refresh hourly


async def _fetch_as_metadata(issuer: str) -> dict:
    """
    OA-1: Fetch the IdP's OIDC discovery document and return an RFC 8414-compliant
    subset for the /.well-known/oauth-authorization-server route.
    Cache is shared with the JWKS machinery (OA-2) so startup only fetches once.
    """
    global _as_metadata_cache, _as_metadata_fetched_at

    now = time.monotonic()
    if _as_metadata_cache and (now - _as_metadata_fetched_at) < _AS_METADATA_TTL:
        return _as_metadata_cache

    discovery_url = f"{issuer.rstrip('/')}/.well-known/openid-configuration"
    async with httpx.AsyncClient() as client:
        resp = await client.get(discovery_url, timeout=10)
        resp.raise_for_status()
        idp = resp.json()

    _as_metadata_cache = {
        "issuer":                           idp.get("issuer", issuer),
        "authorization_endpoint":           idp.get("authorization_endpoint"),
        "token_endpoint":                   idp.get("token_endpoint"),
        "jwks_uri":                         idp.get("jwks_uri"),
        "response_types_supported":         idp.get("response_types_supported", ["code"]),
        "grant_types_supported":            idp.get("grant_types_supported",
                                                ["authorization_code",
                                                 "client_credentials",
                                                 "refresh_token"]),
        "code_challenge_methods_supported": idp.get("code_challenge_methods_supported",
                                                ["S256"]),
        "scopes_supported": [
            "mcp:read", "mcp:operator", "mcp:storage", "mcp:policy", "mcp:system"
        ],
    }
    _as_metadata_fetched_at = now
    logger.info("OA-1: AS metadata cached from %s", discovery_url)
    return _as_metadata_cache


# ── OA-2: JWKS TTL cache ──────────────────────────────────────────────────────
_jwks_cache: Optional[dict] = None
_jwks_uri_cache: Optional[str] = None
_jwks_fetched_at: float = 0.0
_jwks_last_refetch_at: float = 0.0
_JWKS_REFETCH_RATELIMIT: float = 60.0  # seconds between forced re-fetches


async def _get_jwks_with_ttl(issuer: str, jwks_ttl: int) -> dict:
    """
    OA-2: Return the cached JWKS. Re-fetches when:
      • cache is empty
      • cache age > jwks_ttl
    Does NOT re-fetch for kid-miss here; that is handled in _get_key_for_kid().
    """
    global _jwks_cache, _jwks_uri_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < jwks_ttl:
        return _jwks_cache

    # Fetch or refresh — reuses OA-1 cache
    meta = await _fetch_as_metadata(issuer)
    jwks_uri = meta["jwks_uri"]
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri, timeout=10)
        resp.raise_for_status()
        _jwks_cache = dict(resp.json())

    _jwks_uri_cache = jwks_uri
    _jwks_fetched_at = now
    logger.debug("OA-2: JWKS refreshed from %s (%d keys)",
                 jwks_uri, len(_jwks_cache.get("keys", [])))
    return _jwks_cache


async def _get_key_for_kid(issuer: str, jwks_ttl: int, kid: str) -> None:
    """
    OA-2: Ensure the signing key for kid is in the cache.  If the kid is absent
    from the current cache, re-fetch once (rate-limited) before giving up.
    """
    global _jwks_last_refetch_at, _jwks_fetched_at

    jwks = await _get_jwks_with_ttl(issuer, jwks_ttl)
    keys = {k["kid"] for k in jwks.get("keys", []) if "kid" in k}

    if kid not in keys:
        now = time.monotonic()
        if (now - _jwks_last_refetch_at) >= _JWKS_REFETCH_RATELIMIT:
            logger.warning(
                "OA-2: kid '%s' not in JWKS cache — forcing re-fetch "
                "(kid-miss rate-limit resets in %.0fs)",
                kid, _JWKS_REFETCH_RATELIMIT,
            )
            _jwks_last_refetch_at = now
            # Invalidate TTL to force a fresh fetch
            _jwks_fetched_at = 0.0
            await _get_jwks_with_ttl(issuer, jwks_ttl)
        else:
            logger.warning(
                "OA-2: kid '%s' not found; re-fetch rate-limited — "
                "next allowed in %.0fs",
                kid, _JWKS_REFETCH_RATELIMIT - (now - _jwks_last_refetch_at),
            )


# ── OA-4: IdP PKCE capability check ──────────────────────────────────────────

async def _check_idp_pkce_capability(issuer: str) -> None:
    """
    OA-4: Warn if the IdP does not advertise S256 or advertises 'plain'.
    Called once during HTTP startup in main.py.
    """
    try:
        meta = await _fetch_as_metadata(issuer)
        methods = meta.get("code_challenge_methods_supported", [])
    except Exception as exc:
        logger.warning("OA-4: Could not fetch IdP metadata for PKCE check: %s", exc)
        return

    if "S256" not in methods:
        logger.warning(
            "OA-4: IdP at %s does not advertise PKCE S256 support. "
            "Authorization Code + PKCE flows for interactive clients may not work.",
            issuer,
        )
    if "plain" in methods:
        logger.warning(
            "OA-4: IdP at %s advertises insecure PKCE 'plain' method. "
            "Ensure all clients use S256 only.",
            issuer,
        )
    if "S256" in methods and "plain" not in methods:
        logger.info("OA-4: IdP PKCE capability check passed (S256 supported).")


# ── OA-6: Protected-resource metadata document ───────────────────────────────

def _protected_resource_doc(public_url: str, issuer: str) -> dict:
    """OA-6: RFC 9470 protected-resource metadata document."""
    return {
        "resource":                 public_url or issuer,
        "authorization_servers":   [issuer],
        "scopes_supported": [
            "mcp:read", "mcp:operator", "mcp:storage", "mcp:policy", "mcp:system"
        ],
        "bearer_methods_supported": ["header"],
    }


# ── OIDCBearerMiddleware ──────────────────────────────────────────────────────

class OIDCBearerMiddleware:
    """
    INT-2 + OA-2/OA-5/OA-6/OA-7: ASGI middleware that validates OIDC bearer
    tokens on every incoming HTTP request and injects the resolved privilege
    tier, subject, and auth model into request.state.

    Compatible with Starlette's BaseHTTPMiddleware interface.
    """

    def __init__(
        self,
        app,
        issuer: str,
        audience: str,
        jwks_ttl: int = 3600,
        introspection_endpoint: Optional[str] = None,
        introspection_client_id: Optional[str] = None,
        introspection_client_secret: Optional[str] = None,
        introspect_below_ttl: int = 300,
        public_url: Optional[str] = None,
    ):
        self.app                       = app
        self.issuer                    = issuer.rstrip("/")
        self.audience                  = audience
        self.jwks_ttl                  = jwks_ttl
        self.introspection_endpoint    = introspection_endpoint
        self.introspection_client_id   = introspection_client_id or audience
        self.introspection_client_secret = introspection_client_secret
        self.introspect_below_ttl      = introspect_below_ttl
        self.public_url                = (public_url or "").rstrip("/")

    def _unauthorized(self, error: str, message: str):
        """OA-6: Build a 401 JSONResponse with RFC 9470 resource_metadata URI."""
        from starlette.responses import JSONResponse

        www_auth = 'Bearer realm="sp-mcp-server"'
        if self.public_url:
            resource_metadata_uri = (
                f"{self.public_url}/.well-known/oauth-protected-resource"
            )
            www_auth += f', resource_metadata="{resource_metadata_uri}"'

        return JSONResponse(
            {"error": error, "message": message},
            status_code=401,
            headers={"WWW-Authenticate": www_auth},
        )

    async def _introspect(self, token: str, payload: dict) -> bool:
        """
        OA-5: Call the RFC 7662 introspection endpoint.
        Returns True if the token is active, False if revoked.
        Only called when SP_OIDC_INTROSPECTION_ENDPOINT is set AND the
        token's remaining lifetime is below introspect_below_ttl.
        Fail-open: if the endpoint is unreachable, returns True (allows request).
        """
        if not self.introspection_endpoint:
            return True

        exp = payload.get("exp", 0)
        remaining = exp - time.time()
        if remaining > self.introspect_below_ttl:
            return True   # long-lived token — skip introspection this request

        if not self.introspection_client_secret:
            logger.warning(
                "OA-5: SP_OIDC_INTROSPECTION_ENDPOINT is set but "
                "SP_OIDC_INTROSPECTION_CLIENT_SECRET is missing — skipping introspection."
            )
            return True

        try:
            import base64
            creds = base64.b64encode(
                f"{self.introspection_client_id}:{self.introspection_client_secret}"
                .encode()
            ).decode()
            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    self.introspection_endpoint,
                    data={"token": token, "token_type_hint": "access_token"},
                    headers={"Authorization": f"Basic {creds}"},
                    timeout=5,
                )
                resp.raise_for_status()
                result = resp.json()
        except Exception as exc:
            # Fail open — do not block requests if introspection is unavailable
            logger.error(
                "OA-5: Introspection request failed (%s) — "
                "proceeding without revocation check.", exc,
            )
            return True

        active = result.get("active", False)
        if not active:
            logger.warning(
                "OA-5: Token for sub='%s' is revoked (introspection returned active=false).",
                payload.get("sub", "unknown"),
            )
        return active

    async def __call__(self, scope, receive, send):
        from starlette.requests import Request

        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive, send)

        # OA-1/OA-6: Exempt well-known and health endpoints
        if request.url.path in (
            "/health", "/",
            "/.well-known/oauth-authorization-server",
            "/.well-known/oauth-protected-resource",
        ):
            await self.app(scope, receive, send)
            return

        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            response = self._unauthorized("missing_token", "Bearer token required.")
            await response(scope, receive, send)
            return

        token = auth_header[len("Bearer "):]
        try:
            import jwt as pyjwt

            # OA-2: warm up TTL cache; handle kid-miss with rate-limited re-fetch
            await _get_jwks_with_ttl(self.issuer, self.jwks_ttl)
            unverified_header = pyjwt.get_unverified_header(token)
            kid = unverified_header.get("kid", "")
            if kid and kid not in {
                k["kid"] for k in (_jwks_cache or {}).get("keys", []) if "kid" in k
            }:
                await _get_key_for_kid(self.issuer, self.jwks_ttl, kid)

            jwks_client = pyjwt.PyJWKClient(_jwks_uri_cache or
                          (await _fetch_as_metadata(self.issuer))["jwks_uri"])
            signing_key = jwks_client.get_signing_key_from_jwt(token)
            payload = pyjwt.decode(
                token,
                signing_key.key,
                algorithms=["RS256", "ES256"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub", "scope"]},
            )
        except Exception as exc:
            logger.warning("OA-2/INT-2: Token validation failed: %s", exc)
            response = self._unauthorized("invalid_token", str(exc))
            await response(scope, receive, send)
            return

        # OA-5: optional introspection (revocation check)
        if self.introspection_endpoint:
            active = await self._introspect(token, payload)
            if not active:
                response = self._unauthorized("token_revoked", "Token has been revoked.")
                await response(scope, receive, send)
                return

        # Resolve privilege from token scopes (highest wins) — INT-2
        scopes    = payload.get("scope", "").split()
        privilege = "any"
        for scope_claim in scopes:
            tier = SCOPE_PRIVILEGE_MAP.get(scope_claim)
            if tier and _privilege_rank(tier) > _privilege_rank(privilege):
                privilege = tier

        # OA-7: determine auth model from token claims
        auth_model = (
            "oidc_bearer"
            if "preferred_username" in payload
            else "client_credentials"
        )

        scope["state"] = scope.get("state", {})
        scope["state"]["mcp_privilege"]  = privilege
        scope["state"]["mcp_subject"]    = payload.get("sub", "unknown")
        scope["state"]["mcp_auth_model"] = auth_model  # OA-7

        logger.info(
            "INT-2/OA-7: subject='%s' authmodel='%s' privilege='%s' scopes=%s",
            scope["state"]["mcp_subject"], auth_model, privilege, scopes,
        )

        from .mcp_factory import current_audit_user, current_request_privilege, current_auth_model
        user_ctx      = current_audit_user.set(scope["state"]["mcp_subject"])
        privilege_ctx = current_request_privilege.set(privilege)
        auth_model_ctx = current_auth_model.set(auth_model)  # OA-7
        try:
            await self.app(scope, receive, send)
        finally:
            current_request_privilege.reset(privilege_ctx)
            current_audit_user.reset(user_ctx)
            current_auth_model.reset(auth_model_ctx)


def create_http_app(
    mcp_server,
    oidc_issuer: str,
    oidc_audience: str,
    jwks_ttl: int = 3600,
    introspection_endpoint: Optional[str] = None,
    introspection_client_id: Optional[str] = None,
    introspection_client_secret: Optional[str] = None,
    introspect_below_ttl: int = 300,
    public_url: str = "",
):
    """
    INT-2 + OA-1/OA-6: Wrap an MCP server in a Starlette app with OIDC bearer
    auth middleware.  The MCP server's SSE handler is mounted at /mcp.
    Exposes RFC 8414 (OA-1) and RFC 9470 (OA-6) well-known routes.

    Returns a Starlette ASGI application.
    """
    from starlette.applications import Starlette
    from starlette.routing import Route, Mount
    from starlette.requests import Request
    from starlette.responses import JSONResponse
    from mcp.server.sse import SseServerTransport

    sse_transport = SseServerTransport("/mcp/messages")

    async def handle_sse(request: Request):
        async with sse_transport.connect_sse(
            request.scope, request.receive, request._send
        ) as streams:
            await mcp_server.run(
                streams[0],
                streams[1],
                mcp_server.create_initialization_options(),
            )

    async def health(_: Request):
        return JSONResponse({"status": "ok"})

    async def as_metadata(request: Request):
        """GET /.well-known/oauth-authorization-server  (RFC 8414 / MCP 2025-03) — OA-1"""
        try:
            meta = await _fetch_as_metadata(oidc_issuer)
            return JSONResponse(meta)
        except Exception as exc:
            logger.error("OA-1: Failed to fetch AS metadata: %s", exc)
            return JSONResponse(
                {"error": "as_metadata_unavailable", "message": str(exc)},
                status_code=503,
            )

    async def protected_resource_metadata(request: Request):
        """GET /.well-known/oauth-protected-resource  (RFC 9470) — OA-6"""
        doc = _protected_resource_doc(public_url, oidc_issuer)
        return JSONResponse(doc)

    app = Starlette(
        routes=[
            Route("/health",                                        health),
            Route("/.well-known/oauth-authorization-server",       as_metadata),
            Route("/.well-known/oauth-protected-resource",         protected_resource_metadata),
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
        jwks_ttl=jwks_ttl,
        introspection_endpoint=introspection_endpoint,
        introspection_client_id=introspection_client_id,
        introspection_client_secret=introspection_client_secret,
        introspect_below_ttl=introspect_below_ttl,
        public_url=public_url,
    )
    return app
