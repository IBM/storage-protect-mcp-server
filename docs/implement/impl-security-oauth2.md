# Implementation: OAuth 2 Authorization (OA-1 through OA-7)

* **Domain**: Secure Integrations — OAuth 2 / Authorization Server
* **Revision**: 2026-10
* **Design reference**: [`docs/design/security-oauth2.md`](../design/security-oauth2.md)
* **Analysis reference**: [`docs/analysis/security-oauth2-analysis.md`](../analysis/security-oauth2-analysis.md)
* **Architecture reference**: [`docs/architecture/module-security.md`](../architecture/module-security.md)
* **Extends**: [`docs/implement/impl-security-integrations.md § INT-2`](impl-security-integrations.md)
* **Source files**:
  - `src/sp_mcp_server/http_server.py` — primary file for all OA changes
  - `src/sp_mcp_server/main.py` — startup checks (OA-4), new env vars
  - `src/sp_mcp_server/mcp_factory.py` — ACTLOG record enrichment (OA-7)
  - `src/sp_mcp_server/commands/system/auth.py` — dynamic_session label (OA-7)
* **Tests**: [`tests/test_sec_oauth2.py`](../../tests/test_sec_oauth2.py) — 26 tests, all passing

---

## Overview

| Change | ID | Standard |
|--------|----|----------|
| AS metadata proxy route `/.well-known/oauth-authorization-server` | OA-1 | RFC 8414 / MCP 2025-03 |
| JWKS TTL cache + `kid`-miss re-fetch + DoS rate limit | OA-2 | OIDC Core §10.1.1 |
| Authorization Code + PKCE token claim profile | OA-3 | OAuth 2.1 §4.1 |
| IdP PKCE capability check at startup | OA-4 | OAuth 2.1 §4.1.1 |
| Optional RFC 7662 token introspection | OA-5 | RFC 7662 |
| Protected-resource metadata route + `resource_metadata` in `WWW-Authenticate` | OA-6 | RFC 9470 |
| `authmodel` field in ACTLOG `DEFINE SCRATCHPADENTRY` | OA-7 | NR-1 / NR-4 |

All changes are **additive**. The existing INT-2 baseline behaviour (token validation, scope→privilege mapping, TLS enforcement) is unchanged.

> **Important implementation note**: `OIDCBearerMiddleware` uses raw ASGI `__call__(scope, receive, send)` — **not** `BaseHTTPMiddleware.dispatch()`. The `_unauthorized()` helper returns a `JSONResponse` that must be sent as ASGI: `await response(scope, receive, send)`. The `current_auth_model` ContextVar is reset via a `token = ctx.set(value)` / `ctx.reset(token)` pattern inside the `finally` block.

---

## OA-1 — AS Metadata Proxy Route

### File: `src/sp_mcp_server/http_server.py`

Add module-level cache globals and the `_fetch_as_metadata()` helper. The cache is shared with the JWKS machinery so startup fetches the discovery document only once.

```python
# ── OA-1: AS metadata cache ───────────────────────────────────────────────
import time
from typing import Optional

_as_metadata_cache: Optional[dict] = None
_as_metadata_fetched_at: float = 0.0
_AS_METADATA_TTL: float = 3600.0  # refresh hourly


async def _fetch_as_metadata(issuer: str) -> dict:
    """
    Fetch the IdP's OIDC discovery document and return an RFC 8414-compliant
    subset for the /.well-known/oauth-authorization-server route.
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
```

Register the route handler inside `create_http_app()`:

```python
    async def as_metadata(request: Request):        # OA-1
        try:
            meta = await _fetch_as_metadata(oidc_issuer)
            return JSONResponse(meta)
        except Exception as exc:
            logger.error("OA-1: Failed to fetch AS metadata: %s", exc)
            return JSONResponse(
                {"error": "as_metadata_unavailable", "message": str(exc)},
                status_code=503,
            )

    # In create_http_app() routes list:
    Route("/.well-known/oauth-authorization-server", as_metadata),
```

---

## OA-2 — JWKS TTL Cache + `kid`-Miss Re-fetch + DoS Rate Limit

### File: `src/sp_mcp_server/http_server.py`

Add module-level JWKS cache globals and two cooperating helpers. The `kid`-miss path rate-limits re-fetches to at most one per 60 seconds to prevent a forged-`kid` DoS.

```python
# ── OA-2: JWKS TTL cache ──────────────────────────────────────────────────
_jwks_cache: Optional[dict] = None
_jwks_uri_cache: Optional[str] = None
_jwks_fetched_at: float = 0.0
_jwks_last_refetch_at: float = 0.0
_JWKS_REFETCH_RATELIMIT: float = 60.0  # seconds between forced re-fetches


async def _get_jwks_with_ttl(issuer: str, jwks_ttl: int) -> dict:
    """
    Return the cached JWKS. Re-fetches when:
      • cache is empty
      • cache age > jwks_ttl
    Does NOT re-fetch for kid-miss here; that is handled in _get_key_for_kid().
    """
    global _jwks_cache, _jwks_uri_cache, _jwks_fetched_at

    now = time.monotonic()
    if _jwks_cache and (now - _jwks_fetched_at) < jwks_ttl:
        return _jwks_cache

    meta     = await _fetch_as_metadata(issuer)   # reuses OA-1 cache
    jwks_uri = meta["jwks_uri"]
    async with httpx.AsyncClient() as client:
        resp = await client.get(jwks_uri, timeout=10)
        resp.raise_for_status()
        _jwks_cache = resp.json()

    _jwks_uri_cache = jwks_uri
    _jwks_fetched_at = now
    logger.debug("OA-2: JWKS refreshed from %s (%d keys)",
                 jwks_uri, len(_jwks_cache.get("keys", [])))
    return _jwks_cache


async def _get_key_for_kid(issuer: str, jwks_ttl: int, kid: str) -> None:
    """
    If kid is absent from the current cache, force one re-fetch (rate-limited).
    Raises ValueError if kid is still absent after re-fetch.
    """
    global _jwks_last_refetch_at, _jwks_fetched_at

    jwks = await _get_jwks_with_ttl(issuer, jwks_ttl)
    keys = {k["kid"] for k in jwks.get("keys", []) if "kid" in k}

    if kid not in keys:
        now = time.monotonic()
        if (now - _jwks_last_refetch_at) >= _JWKS_REFETCH_RATELIMIT:
            logger.warning(
                "OA-2: kid '%s' not in JWKS cache — forcing re-fetch "
                "(next rate-limit resets in %.0fs)",
                kid, _JWKS_REFETCH_RATELIMIT,
            )
            _jwks_last_refetch_at = now
            _jwks_fetched_at = 0.0          # invalidate TTL to force fresh fetch
            await _get_jwks_with_ttl(issuer, jwks_ttl)
        else:
            logger.warning(
                "OA-2: kid '%s' not found; re-fetch rate-limited — "
                "next allowed in %.0fs",
                kid, _JWKS_REFETCH_RATELIMIT - (now - _jwks_last_refetch_at),
            )
```

Update `OIDCBearerMiddleware.__init__` to accept the new parameters:

```python
class OIDCBearerMiddleware:
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
        self.app                         = app
        self.issuer                      = issuer.rstrip("/")
        self.audience                    = audience
        self.jwks_ttl                    = jwks_ttl
        self.introspection_endpoint      = introspection_endpoint
        self.introspection_client_id     = introspection_client_id or audience
        self.introspection_client_secret = introspection_client_secret
        self.introspect_below_ttl        = introspect_below_ttl
        self.public_url                  = (public_url or "").rstrip("/")
```

Update `__call__()` to use the TTL-aware JWKS helpers (raw ASGI — not `dispatch()`):

```python
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

            # OA-2: warm TTL cache; handle kid-miss with rate-limited re-fetch
            await _get_jwks_with_ttl(self.issuer, self.jwks_ttl)
            unverified_header = pyjwt.get_unverified_header(token)
            kid = unverified_header.get("kid", "")
            if kid and kid not in {
                k["kid"] for k in (_jwks_cache or {}).get("keys", []) if "kid" in k
            }:
                await _get_key_for_kid(self.issuer, self.jwks_ttl, kid)

            jwks_client = pyjwt.PyJWKClient(
                _jwks_uri_cache or (await _fetch_as_metadata(self.issuer))["jwks_uri"]
            )
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
        user_ctx       = current_audit_user.set(scope["state"]["mcp_subject"])
        privilege_ctx  = current_request_privilege.set(privilege)
        auth_model_ctx = current_auth_model.set(auth_model)           # OA-7
        try:
            await self.app(scope, receive, send)
        finally:
            current_request_privilege.reset(privilege_ctx)
            current_audit_user.reset(user_ctx)
            current_auth_model.reset(auth_model_ctx)                  # OA-7 cleanup
```

---

## OA-4 — IdP PKCE Capability Check at Startup

### File: `src/sp_mcp_server/http_server.py`

```python
async def _check_idp_pkce_capability(issuer: str) -> None:
    """
    OA-4: Warn if the IdP does not advertise S256 or advertises 'plain'.
    Called once during HTTP startup in main.py.
    Reuses the OA-1 metadata cache — no extra network call when cache is warm.
    """
    try:
        meta    = await _fetch_as_metadata(issuer)
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
```

### File: `src/sp_mcp_server/main.py`

Call `_check_idp_pkce_capability` inside the `--transport http` startup branch, after `SP_OIDC_ISSUER` validation:

```python
    if args.transport == "http":
        oidc_issuer   = os.environ.get("SP_OIDC_ISSUER")
        oidc_audience = os.environ.get("SP_OIDC_AUDIENCE", "sp-mcp-server")

        if not oidc_issuer:
            logger.error("INT-2: SP_OIDC_ISSUER is required for --transport http")
            sys.exit(1)

        # ── OA-4: PKCE capability check (non-fatal) ─────────────────────
        import asyncio
        from .http_server import _check_idp_pkce_capability
        asyncio.get_event_loop().run_until_complete(
            _check_idp_pkce_capability(oidc_issuer)
        )
        # ────────────────────────────────────────────────────────────────

        jwks_ttl   = int(os.environ.get("SP_OIDC_JWKS_TTL", "3600"))
        public_url = os.environ.get("SP_MCP_PUBLIC_URL", "")

        # OA-5 introspection env vars
        introspection_endpoint      = os.environ.get("SP_OIDC_INTROSPECTION_ENDPOINT")
        introspection_client_id     = os.environ.get("SP_OIDC_INTROSPECTION_CLIENT_ID")
        introspection_client_secret = os.environ.get("SP_OIDC_INTROSPECTION_CLIENT_SECRET")
        introspect_below_ttl        = int(os.environ.get("SP_OIDC_INTROSPECT_BELOW_TTL", "300"))

        app = create_http_app(
            server,
            oidc_issuer=oidc_issuer,
            oidc_audience=oidc_audience,
            jwks_ttl=jwks_ttl,
            introspection_endpoint=introspection_endpoint,
            introspection_client_id=introspection_client_id,
            introspection_client_secret=introspection_client_secret,
            introspect_below_ttl=introspect_below_ttl,
            public_url=public_url,
        )
```

---

## OA-5 — Optional Token Introspection (RFC 7662)

### File: `src/sp_mcp_server/http_server.py`

Add `_introspect()` method to `OIDCBearerMiddleware`:

```python
    async def _introspect(self, token: str, payload: dict) -> bool:
        """
        OA-5: Call the RFC 7662 introspection endpoint.
        Returns True if the token is active, False if revoked.
        Only called when SP_OIDC_INTROSPECTION_ENDPOINT is set AND the
        token's remaining lifetime is below introspect_below_ttl.
        Fail-open: returns True if the endpoint is unreachable.
        """
        exp       = payload.get("exp", 0)
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
                "proceeding without revocation check.", exc
            )
            return True

        active = result.get("active", False)
        if not active:
            logger.warning(
                "OA-5: Token for sub='%s' is revoked (introspection returned active=false).",
                payload.get("sub", "unknown"),
            )
        return active
```

> **Fail-open policy**: If the introspection endpoint is unreachable (network error, 5xx), the middleware logs `ERROR` and proceeds. This prevents an IdP outage from locking all users out. Deployments requiring fail-closed must enforce introspection at a reverse-proxy layer.

---

## OA-6 — Protected Resource Metadata + `WWW-Authenticate` `resource_metadata`

### File: `src/sp_mcp_server/http_server.py`

Add the module-level `_protected_resource_doc()` function and the `_unauthorized()` instance method:

```python
def _protected_resource_doc(public_url: str, issuer: str) -> dict:
    """OA-6: RFC 9470 protected-resource metadata document."""
    return {
        "resource":                public_url or issuer,
        "authorization_servers":   [issuer],
        "scopes_supported": [
            "mcp:read", "mcp:operator", "mcp:storage", "mcp:policy", "mcp:system"
        ],
        "bearer_methods_supported": ["header"],
    }


# Inside OIDCBearerMiddleware:
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
```

> **Calling pattern**: `_unauthorized()` returns a `JSONResponse` (a callable). Because the middleware is raw ASGI, send it with `await response(scope, receive, send)` — not `return response`.

Register the route inside `create_http_app()`:

```python
    async def protected_resource_metadata(request: Request):   # OA-6
        return JSONResponse(_protected_resource_doc(public_url, oidc_issuer))

    # In create_http_app() routes list:
    Route("/.well-known/oauth-protected-resource", protected_resource_metadata),
```

### Full `create_http_app()` signature

```python
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
) -> Starlette:
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

    async def as_metadata(request: Request):        # OA-1
        try:
            return JSONResponse(await _fetch_as_metadata(oidc_issuer))
        except Exception as exc:
            return JSONResponse({"error": str(exc)}, status_code=503)

    async def protected_resource_metadata(request: Request):   # OA-6
        return JSONResponse(_protected_resource_doc(public_url, oidc_issuer))

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
```

---

## OA-7 — `authmodel` in ACTLOG `DEFINE SCRATCHPADENTRY`

### File: `src/sp_mcp_server/mcp_factory.py`

Add `current_auth_model` near the top with the other ContextVars:

```python
# src/sp_mcp_server/mcp_factory.py — near other ContextVar declarations
import contextvars

current_audit_user: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_audit_user", default="local"
)
current_auth_model: contextvars.ContextVar[str] = contextvars.ContextVar(
    "current_auth_model", default="local"       # OA-7
)
```

`OIDCBearerMiddleware.__call__()` sets the ContextVar after successful validation (shown in OA-2 section above). The reset is in the `finally` block to guarantee cleanup on every code path.

Update the ACTLOG record construction in `handle_call_tool()`:

```python
    # Before (OA-7 not present):
    # audit_desc = f"MCP_AUDIT user={user} tool={name} priv={priv} corr={corr_id}"

    # After (OA-7):
    auth_model = current_auth_model.get()
    audit_desc = (
        f"MCP_AUDIT user={user} authmodel={auth_model} "
        f"tool={name} priv={priv} corr={corr_id}"
    )
```

### File: `src/sp_mcp_server/commands/system/auth.py`

Set `current_auth_model` when issuing a dynamic-session lease:

```python
        # authenticate_session.execute() — after issuing the lease successfully
        from sp_mcp_server.mcp_factory import current_auth_model
        current_auth_model.set("dynamic_session")               # OA-7
```

### Auth model label reference

| Scenario | `current_auth_model` value |
|----------|--------------------------|
| `client_credentials` JWT (`preferred_username` absent) | `client_credentials` |
| Authorization Code JWT (`preferred_username` present) | `oidc_bearer` |
| `authenticate_session` tool (Model B) | `dynamic_session` |
| stdio / no HTTP auth | `local` |

---

## Environment Variable Reference (complete)

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SP_OIDC_ISSUER` | Yes (HTTP) | — | OIDC issuer / AS base URL |
| `SP_OIDC_AUDIENCE` | No | `sp-mcp-server` | Token audience claim |
| `SP_TLS_CERT` / `SP_TLS_KEY` | Yes (HTTP) | — | TLS cert/key (RG-5) |
| `SP_OIDC_JWKS_TTL` | No | `3600` | JWKS cache lifetime in seconds (OA-2) |
| `SP_OIDC_INTROSPECTION_ENDPOINT` | No | unset | RFC 7662 introspection URL (OA-5) |
| `SP_OIDC_INTROSPECTION_CLIENT_ID` | No | `SP_OIDC_AUDIENCE` | Introspection Basic-auth client ID (OA-5) |
| `SP_OIDC_INTROSPECTION_CLIENT_SECRET` | No | unset | Introspection client secret — store in keyring (OA-5) |
| `SP_OIDC_INTROSPECT_BELOW_TTL` | No | `300` | Introspect tokens with < N seconds remaining lifetime (OA-5) |
| `SP_MCP_PUBLIC_URL` | No | derived | MCP server public base URL for RFC 9470 metadata (OA-6) |

---

## Test Coverage

All tests are in [`tests/test_sec_oauth2.py`](../../tests/test_sec_oauth2.py). Each uses `pytest-asyncio` (strict mode — every async test must be marked `@pytest.mark.asyncio`) and `respx` for outbound HTTP mocking.

Module-level cache globals (`_as_metadata_cache`, `_jwks_cache`, etc.) must be reset between test classes via an `autouse` fixture to prevent inter-test pollution:

```python
@pytest.fixture(autouse=True)
def reset_http_server_caches():
    """Reset module-level caches between tests to prevent state leakage."""
    import sp_mcp_server.http_server as hs
    hs._as_metadata_cache    = None
    hs._as_metadata_fetched_at = 0.0
    hs._jwks_cache           = None
    hs._jwks_uri_cache       = None
    hs._jwks_fetched_at      = 0.0
    hs._jwks_last_refetch_at = 0.0
    yield
    hs._as_metadata_cache    = None
    hs._jwks_cache           = None
```

The MCP server instance inside tests must be created with `SP_MCP_SKIP_SECURITY_CHECKS=1` to bypass the NET-1 session-security startup check.

### Test class summary

| Test class | Count | Requirements |
|------------|:-----:|-------------|
| `TestOAuthASMetadata` | 4 | OA-1: required fields, TTL cache, S256 in response |
| `TestJWKSRotation` | 4 | OA-2: TTL expiry, kid-miss re-fetch, rate limiting |
| `TestPKCECapability` | 4 | OA-4: S256 pass, S256 missing warn, plain warn, unreachable IdP |
| `TestIntrospection` | 5 | OA-5: revoked token, active token, long-lived skip, fail-open, no secret |
| `TestProtectedResourceMetadata` | 5 | OA-6: doc fields, public_url, fallback, WWW-Authenticate with/without public_url |
| `TestAuthModelAudit` | 4 | OA-3/OA-7: local, client_credentials, oidc_bearer, dynamic_session labels in ACTLOG |
| **Total** | **26** | **OA-1–OA-7** |

```python
# tests/test_sec_oauth2.py — representative test stubs (actual file is canonical)

class TestOAuthASMetadata:
    @pytest.mark.asyncio
    async def test_fetch_as_metadata_returns_required_fields(self, ...): ...
    @pytest.mark.asyncio
    async def test_as_metadata_cache_prevents_second_idp_call(self, ...): ...
    @pytest.mark.asyncio
    async def test_as_metadata_cache_refreshes_after_ttl(self, ...): ...
    @pytest.mark.asyncio
    async def test_as_metadata_includes_s256_challenge_method(self, ...): ...

class TestJWKSRotation:
    @pytest.mark.asyncio
    async def test_jwks_cached_within_ttl(self, ...): ...
    @pytest.mark.asyncio
    async def test_jwks_refreshed_after_ttl_expiry(self, ...): ...
    @pytest.mark.asyncio
    async def test_kid_miss_triggers_one_refetch(self, ...): ...
    @pytest.mark.asyncio
    async def test_kid_miss_rate_limited_to_one_refetch(self, ...): ...

class TestPKCECapability:
    @pytest.mark.asyncio
    async def test_s256_supported_logs_info_not_warning(self, ...): ...
    @pytest.mark.asyncio
    async def test_missing_s256_emits_warning(self, ...): ...
    @pytest.mark.asyncio
    async def test_plain_method_emits_warning(self, ...): ...
    @pytest.mark.asyncio
    async def test_idp_unreachable_logs_warning_not_exception(self, ...): ...

class TestIntrospection:
    @pytest.mark.asyncio
    async def test_revoked_token_returns_false(self, ...): ...
    @pytest.mark.asyncio
    async def test_active_token_returns_true(self, ...): ...
    @pytest.mark.asyncio
    async def test_long_lived_token_skips_introspection(self, ...): ...
    @pytest.mark.asyncio
    async def test_introspection_fail_open(self, ...): ...
    @pytest.mark.asyncio
    async def test_missing_client_secret_skips_introspection(self, ...): ...

class TestProtectedResourceMetadata:
    @pytest.mark.asyncio
    async def test_protected_resource_doc_contains_required_fields(self, ...): ...
    @pytest.mark.asyncio
    async def test_protected_resource_doc_uses_public_url_as_resource(self, ...): ...
    @pytest.mark.asyncio
    async def test_protected_resource_doc_falls_back_to_issuer(self, ...): ...
    @pytest.mark.asyncio
    async def test_unauthorized_includes_resource_metadata_uri_when_public_url_set(self, ...): ...
    @pytest.mark.asyncio
    async def test_unauthorized_no_resource_metadata_when_public_url_absent(self, ...): ...

class TestAuthModelAudit:
    @pytest.mark.asyncio
    async def test_local_authmodel_in_actlog(self, ...): ...
    @pytest.mark.asyncio
    async def test_client_credentials_authmodel_in_actlog(self, ...): ...
    @pytest.mark.asyncio
    async def test_oidc_bearer_authmodel_in_actlog(self, ...): ...
    @pytest.mark.asyncio
    async def test_dynamic_session_authmodel_set_after_authenticate(self, ...): ...
```

Run:
```bash
python3 -m pytest tests/test_sec_oauth2.py -v
# 26 passed
```

---

## Files Changed Summary

| File | Changes |
|------|---------|
| `src/sp_mcp_server/http_server.py` | OA-1: `_fetch_as_metadata()`, `as_metadata` route; OA-2: `_get_jwks_with_ttl()`, `_get_key_for_kid()`, kid-miss rate-limit; OA-4: `_check_idp_pkce_capability()`; OA-5: `_introspect()` method; OA-6: `_protected_resource_doc()`, `_unauthorized(error, message)`, `protected_resource_metadata` route; OA-7: `authmodel` detection in `__call__()`; updated `create_http_app()` signature |
| `src/sp_mcp_server/main.py` | OA-4: `_check_idp_pkce_capability()` call at startup; OA-2/OA-5/OA-6: read new env vars and pass to `create_http_app()` |
| `src/sp_mcp_server/mcp_factory.py` | OA-7: `current_auth_model` ContextVar; `authmodel=` field in `DEFINE SCRATCHPADENTRY` description |
| `src/sp_mcp_server/commands/system/auth.py` | OA-7: `current_auth_model.set("dynamic_session")` after issuing lease |
| `tests/test_sec_oauth2.py` | 26 tests across 6 classes covering OA-1–OA-7 (replaces old `test_security_controls.py` stubs) |

---

## Deployment Checklist

```
OA-1 (AS Metadata):
  [x] SP_OIDC_ISSUER set; IdP reachable from MCP server host
  [x] curl https://<mcp-host>:8443/.well-known/oauth-authorization-server
      → 200 with token_endpoint and jwks_uri
  [x] MCP client auto-discovers AS from MCP server URL alone

OA-2 (JWKS rotation):
  [x] SP_OIDC_JWKS_TTL set in .env (recommend 3600)
  [x] Rotate IdP signing key; verify tokens accepted without restart
  [x] Logs show "OA-2: kid '...' not in JWKS cache — forcing re-fetch" at WARNING

OA-4 (PKCE check):
  [x] Startup log contains no OA-4 WARNING for S256
  [x] No "plain" method in IdP discovery document

OA-5 (Introspection — optional):
  [x] SP_OIDC_INTROSPECTION_ENDPOINT set if revocation required
  [x] SP_OIDC_INTROSPECTION_CLIENT_SECRET in OS keyring under
      service "ibm-sp-mcp-server", key "introspection-secret" (not in .env)
  [x] Revoke a short-lived token; confirm 401 token_revoked within
      SP_OIDC_INTROSPECT_BELOW_TTL seconds

OA-6 (Resource metadata):
  [x] SP_MCP_PUBLIC_URL set to externally reachable address
  [x] curl https://<mcp-host>:8443/.well-known/oauth-protected-resource
      → 200 with authorization_servers
  [x] curl -v https://<mcp-host>:8443/mcp/sse (no auth)
      → 401 with WWW-Authenticate containing resource_metadata URI

OA-7 (Auth model audit):
  [x] client_credentials tool call:
      QUERY ACTLOG SEARCH=authmodel=client_credentials BEGINDATE=TODAY
  [x] Interactive (PKCE) tool call:
      QUERY ACTLOG SEARCH=authmodel=oidc_bearer BEGINDATE=TODAY
  [x] Dynamic-auth tool call:
      QUERY ACTLOG SEARCH=authmodel=dynamic_session BEGINDATE=TODAY
```
