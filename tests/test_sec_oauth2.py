"""
Security-control regression tests — OAuth 2 authorization (OA-1 through OA-7).

Controls covered:
  OA-1  /.well-known/oauth-authorization-server returns RFC 8414 metadata
  OA-2  JWKS TTL cache + kid-miss re-fetch + DoS rate limit
  OA-4  IdP PKCE capability check at startup
  OA-5  Optional RFC 7662 token introspection (revocation)
  OA-6  /.well-known/oauth-protected-resource + resource_metadata in WWW-Authenticate
  OA-7  authmodel= field in ACTLOG DEFINE SCRATCHPADENTRY

References:
  docs/design/security-oauth2.md
  docs/implement/impl-security-oauth2.md
"""

from __future__ import annotations

import time
import pytest
import pytest_asyncio
import httpx

# ---------------------------------------------------------------------------
# Helpers / constants
# ---------------------------------------------------------------------------

FAKE_ISSUER = "https://idp.example.com/realms/test"
FAKE_AUDIENCE = "sp-mcp-server"
FAKE_JWKS_URI = f"{FAKE_ISSUER}/protocol/openid-connect/certs"
FAKE_TOKEN_ENDPOINT = f"{FAKE_ISSUER}/protocol/openid-connect/token"
FAKE_AUTH_ENDPOINT = f"{FAKE_ISSUER}/protocol/openid-connect/auth"
FAKE_PUBLIC_URL = "https://sp-mcp.example.com:8443"


def _discovery_doc(
    issuer: str = FAKE_ISSUER,
    jwks_uri: str = FAKE_JWKS_URI,
    pkce_methods: list | None = None,
) -> dict:
    """Return a minimal OIDC discovery document."""
    if pkce_methods is None:
        pkce_methods = ["S256"]
    return {
        "issuer": issuer,
        "authorization_endpoint": FAKE_AUTH_ENDPOINT,
        "token_endpoint": FAKE_TOKEN_ENDPOINT,
        "jwks_uri": jwks_uri,
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "client_credentials", "refresh_token"],
        "code_challenge_methods_supported": pkce_methods,
    }


# ---------------------------------------------------------------------------
# Module-level cache reset fixture
# Reset the http_server module-level caches between tests to avoid ordering
# dependencies.
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def reset_http_server_caches():
    """Reset all module-level caches in http_server before each test."""
    import sp_mcp_server.http_server as hs
    hs._as_metadata_cache = None
    hs._as_metadata_fetched_at = 0.0
    hs._jwks_cache = None
    hs._jwks_uri_cache = None
    hs._jwks_fetched_at = 0.0
    hs._jwks_last_refetch_at = 0.0
    yield
    hs._as_metadata_cache = None
    hs._as_metadata_fetched_at = 0.0
    hs._jwks_cache = None
    hs._jwks_uri_cache = None
    hs._jwks_fetched_at = 0.0
    hs._jwks_last_refetch_at = 0.0


# ---------------------------------------------------------------------------
# OA-1 — AS Metadata Proxy Route
# ---------------------------------------------------------------------------

class TestOAuthASMetadata:
    """OA-1: /.well-known/oauth-authorization-server RFC 8414 metadata."""

    @pytest.mark.asyncio
    async def test_fetch_as_metadata_returns_required_fields(self, respx_mock):
        """OA-1: _fetch_as_metadata returns token_endpoint, jwks_uri, and scopes_supported."""
        from sp_mcp_server.http_server import _fetch_as_metadata

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc())
        )

        meta = await _fetch_as_metadata(FAKE_ISSUER)

        assert meta["token_endpoint"] == FAKE_TOKEN_ENDPOINT
        assert meta["jwks_uri"] == FAKE_JWKS_URI
        assert "mcp:read" in meta["scopes_supported"]
        assert "mcp:system" in meta["scopes_supported"]

    @pytest.mark.asyncio
    async def test_as_metadata_cache_prevents_second_idp_call(self, respx_mock):
        """OA-1: Second call within TTL does not re-fetch from IdP."""
        from sp_mcp_server.http_server import _fetch_as_metadata

        route = respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc())
        )

        await _fetch_as_metadata(FAKE_ISSUER)
        await _fetch_as_metadata(FAKE_ISSUER)

        # IdP discovery endpoint must have been called exactly once
        assert route.call_count == 1

    @pytest.mark.asyncio
    async def test_as_metadata_cache_refreshes_after_ttl(self, respx_mock, monkeypatch):
        """OA-1: Cache older than _AS_METADATA_TTL causes a re-fetch."""
        import sp_mcp_server.http_server as hs
        from sp_mcp_server.http_server import _fetch_as_metadata

        route = respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc())
        )

        await _fetch_as_metadata(FAKE_ISSUER)
        assert route.call_count == 1

        # Advance fetched_at so the cache appears stale
        monkeypatch.setattr(hs, "_as_metadata_fetched_at", time.monotonic() - hs._AS_METADATA_TTL - 1)

        await _fetch_as_metadata(FAKE_ISSUER)
        assert route.call_count == 2

    @pytest.mark.asyncio
    async def test_as_metadata_includes_s256_challenge_method(self, respx_mock):
        """OA-1: Metadata advertises code_challenge_methods_supported containing S256."""
        from sp_mcp_server.http_server import _fetch_as_metadata

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc())
        )

        meta = await _fetch_as_metadata(FAKE_ISSUER)
        assert "S256" in meta["code_challenge_methods_supported"]


# ---------------------------------------------------------------------------
# OA-2 — JWKS TTL Cache + kid-miss re-fetch + DoS rate limit
# ---------------------------------------------------------------------------

class TestJWKSRotation:
    """OA-2: JWKS cache TTL, kid-miss re-fetch, and re-fetch rate limit."""

    def _jwks_doc(self, kids: list[str]) -> dict:
        return {"keys": [{"kid": k, "kty": "RSA", "use": "sig"} for k in kids]}

    @pytest.mark.asyncio
    async def test_jwks_cached_within_ttl(self, respx_mock):
        """OA-2: JWKS is not re-fetched while cache is within TTL."""
        from sp_mcp_server.http_server import _get_jwks_with_ttl

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc())
        )
        jwks_route = respx_mock.get(FAKE_JWKS_URI).mock(
            return_value=httpx.Response(200, json=self._jwks_doc(["key1"]))
        )

        await _get_jwks_with_ttl(FAKE_ISSUER, jwks_ttl=3600)
        await _get_jwks_with_ttl(FAKE_ISSUER, jwks_ttl=3600)

        assert jwks_route.call_count == 1

    @pytest.mark.asyncio
    async def test_jwks_refreshed_after_ttl_expiry(self, respx_mock, monkeypatch):
        """OA-2: JWKS is re-fetched when cache age >= jwks_ttl."""
        import sp_mcp_server.http_server as hs
        from sp_mcp_server.http_server import _get_jwks_with_ttl

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc())
        )
        jwks_route = respx_mock.get(FAKE_JWKS_URI).mock(
            return_value=httpx.Response(200, json=self._jwks_doc(["key1"]))
        )

        await _get_jwks_with_ttl(FAKE_ISSUER, jwks_ttl=3600)
        assert jwks_route.call_count == 1

        # Make cache appear expired
        monkeypatch.setattr(hs, "_jwks_fetched_at", time.monotonic() - 3601)

        await _get_jwks_with_ttl(FAKE_ISSUER, jwks_ttl=3600)
        assert jwks_route.call_count == 2

    @pytest.mark.asyncio
    async def test_kid_miss_triggers_one_refetch(self, respx_mock):
        """OA-2: Unknown kid causes exactly one immediate re-fetch."""
        import sp_mcp_server.http_server as hs
        from sp_mcp_server.http_server import _get_jwks_with_ttl, _get_key_for_kid

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc())
        )
        # First call: returns only "key1".  Second call (re-fetch): returns "new-key" too.
        jwks_route = respx_mock.get(FAKE_JWKS_URI).mock(
            side_effect=[
                httpx.Response(200, json=self._jwks_doc(["key1"])),
                httpx.Response(200, json=self._jwks_doc(["key1", "new-key"])),
            ]
        )

        # Warm up cache — only "key1" in cache now
        await _get_jwks_with_ttl(FAKE_ISSUER, jwks_ttl=3600)
        assert jwks_route.call_count == 1

        # "new-key" is absent → should trigger one re-fetch
        await _get_key_for_kid(FAKE_ISSUER, jwks_ttl=3600, kid="new-key")

        # Exactly one extra JWKS call
        assert jwks_route.call_count == 2

    @pytest.mark.asyncio
    async def test_kid_miss_rate_limited_to_one_refetch(self, respx_mock):
        """OA-2: Multiple unknown kids within 60 s trigger at most one re-fetch."""
        from sp_mcp_server.http_server import _get_jwks_with_ttl, _get_key_for_kid

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc())
        )
        jwks_route = respx_mock.get(FAKE_JWKS_URI).mock(
            return_value=httpx.Response(200, json=self._jwks_doc(["key1"]))
        )

        # Warm cache
        await _get_jwks_with_ttl(FAKE_ISSUER, jwks_ttl=3600)
        after_warm = jwks_route.call_count

        # First unknown kid: allowed re-fetch
        await _get_key_for_kid(FAKE_ISSUER, jwks_ttl=3600, kid="unknown-1")
        # Second unknown kid within rate-limit window: should NOT re-fetch again
        await _get_key_for_kid(FAKE_ISSUER, jwks_ttl=3600, kid="unknown-2")
        await _get_key_for_kid(FAKE_ISSUER, jwks_ttl=3600, kid="unknown-3")

        # At most one extra JWKS fetch after cache warm-up (rate-limited)
        assert jwks_route.call_count <= after_warm + 1


# ---------------------------------------------------------------------------
# OA-4 — IdP PKCE Capability Check at Startup
# ---------------------------------------------------------------------------

class TestPKCECapability:
    """OA-4: _check_idp_pkce_capability emits appropriate log messages."""

    @pytest.mark.asyncio
    async def test_s256_supported_logs_info_not_warning(self, respx_mock, caplog):
        """OA-4: IdP with S256 (no plain) logs INFO, no WARNING."""
        from sp_mcp_server.http_server import _check_idp_pkce_capability

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc(pkce_methods=["S256"]))
        )

        with caplog.at_level("DEBUG", logger="sp_mcp_server.http_server"):
            await _check_idp_pkce_capability(FAKE_ISSUER)

        warning_texts = [r.message for r in caplog.records if r.levelname == "WARNING"]
        assert not any("S256" in t for t in warning_texts), (
            "Should not warn about S256 when it is supported"
        )
        assert any("passed" in r.message for r in caplog.records if r.levelname == "INFO")

    @pytest.mark.asyncio
    async def test_missing_s256_emits_warning(self, respx_mock, caplog):
        """OA-4: IdP without S256 advertised logs a WARNING."""
        from sp_mcp_server.http_server import _check_idp_pkce_capability

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc(pkce_methods=[]))
        )

        with caplog.at_level("WARNING", logger="sp_mcp_server.http_server"):
            await _check_idp_pkce_capability(FAKE_ISSUER)

        assert any("S256" in r.message for r in caplog.records if r.levelname == "WARNING")

    @pytest.mark.asyncio
    async def test_plain_method_emits_warning(self, respx_mock, caplog):
        """OA-4: IdP advertising 'plain' PKCE logs a WARNING."""
        from sp_mcp_server.http_server import _check_idp_pkce_capability

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            return_value=httpx.Response(200, json=_discovery_doc(pkce_methods=["S256", "plain"]))
        )

        with caplog.at_level("WARNING", logger="sp_mcp_server.http_server"):
            await _check_idp_pkce_capability(FAKE_ISSUER)

        assert any("plain" in r.message for r in caplog.records if r.levelname == "WARNING")

    @pytest.mark.asyncio
    async def test_idp_unreachable_logs_warning_not_exception(self, respx_mock, caplog):
        """OA-4: Network failure during PKCE check logs WARNING and does not raise."""
        from sp_mcp_server.http_server import _check_idp_pkce_capability

        respx_mock.get(f"{FAKE_ISSUER}/.well-known/openid-configuration").mock(
            side_effect=httpx.ConnectError("unreachable")
        )

        with caplog.at_level("WARNING", logger="sp_mcp_server.http_server"):
            # Must not raise
            await _check_idp_pkce_capability(FAKE_ISSUER)

        assert any("OA-4" in r.message for r in caplog.records if r.levelname == "WARNING")


# ---------------------------------------------------------------------------
# OA-5 — Optional Token Introspection
# ---------------------------------------------------------------------------

class TestIntrospection:
    """OA-5: RFC 7662 introspection — revocation check and threshold logic."""

    def _make_middleware(
        self,
        introspection_endpoint: str = "https://idp.example.com/introspect",
        introspection_client_secret: str = "secret",
        introspect_below_ttl: int = 300,
    ):
        from sp_mcp_server.http_server import OIDCBearerMiddleware
        from unittest.mock import MagicMock

        mw = OIDCBearerMiddleware.__new__(OIDCBearerMiddleware)
        mw.app = MagicMock()
        mw.issuer = FAKE_ISSUER
        mw.audience = FAKE_AUDIENCE
        mw.jwks_ttl = 3600
        mw.introspection_endpoint = introspection_endpoint
        mw.introspection_client_id = FAKE_AUDIENCE
        mw.introspection_client_secret = introspection_client_secret
        mw.introspect_below_ttl = introspect_below_ttl
        mw.public_url = ""
        return mw

    @pytest.mark.asyncio
    async def test_revoked_token_returns_false(self, respx_mock):
        """OA-5: Introspection returning active=false → _introspect returns False."""
        mw = self._make_middleware()
        respx_mock.post("https://idp.example.com/introspect").mock(
            return_value=httpx.Response(200, json={"active": False})
        )

        # Short-lived token so remaining TTL < introspect_below_ttl
        payload = {"sub": "alice", "exp": int(time.time()) + 60}
        result = await mw._introspect("fake-token", payload)

        assert result is False

    @pytest.mark.asyncio
    async def test_active_token_returns_true(self, respx_mock):
        """OA-5: Introspection returning active=true → _introspect returns True."""
        mw = self._make_middleware()
        respx_mock.post("https://idp.example.com/introspect").mock(
            return_value=httpx.Response(200, json={"active": True})
        )

        payload = {"sub": "alice", "exp": int(time.time()) + 60}
        result = await mw._introspect("fake-token", payload)

        assert result is True

    @pytest.mark.asyncio
    async def test_long_lived_token_skips_introspection(self, respx_mock):
        """OA-5: Token with remaining TTL > threshold skips introspection call."""
        mw = self._make_middleware(introspect_below_ttl=300)
        introspect_route = respx_mock.post("https://idp.example.com/introspect").mock(
            return_value=httpx.Response(200, json={"active": True})
        )

        # Token expires far in the future — well above the 300 s threshold
        payload = {"sub": "alice", "exp": int(time.time()) + 3600}
        result = await mw._introspect("fake-token", payload)

        assert result is True
        assert introspect_route.call_count == 0

    @pytest.mark.asyncio
    async def test_introspection_fail_open(self, respx_mock):
        """OA-5: Introspection endpoint unreachable → fail-open (returns True)."""
        mw = self._make_middleware()
        respx_mock.post("https://idp.example.com/introspect").mock(
            side_effect=httpx.ConnectError("endpoint unreachable")
        )

        payload = {"sub": "alice", "exp": int(time.time()) + 60}
        result = await mw._introspect("fake-token", payload)

        # Fail-open: request proceeds even when introspection is unavailable
        assert result is True

    @pytest.mark.asyncio
    async def test_missing_client_secret_skips_introspection(self, respx_mock, caplog):
        """OA-5: Missing client secret skips introspection with WARNING."""
        mw = self._make_middleware(introspection_client_secret="")
        introspect_route = respx_mock.post("https://idp.example.com/introspect").mock(
            return_value=httpx.Response(200, json={"active": False})
        )

        payload = {"sub": "alice", "exp": int(time.time()) + 60}
        with caplog.at_level("WARNING", logger="sp_mcp_server.http_server"):
            result = await mw._introspect("fake-token", payload)

        assert result is True
        assert introspect_route.call_count == 0
        assert any("SECRET" in r.message.upper() or "secret" in r.message
                   for r in caplog.records if r.levelname == "WARNING")


# ---------------------------------------------------------------------------
# OA-6 — Protected Resource Metadata + WWW-Authenticate resource_metadata
# ---------------------------------------------------------------------------

class TestProtectedResourceMetadata:
    """OA-6: RFC 9470 protected-resource metadata and WWW-Authenticate header."""

    def test_protected_resource_doc_contains_required_fields(self):
        """OA-6: _protected_resource_doc returns authorization_servers and scopes_supported."""
        from sp_mcp_server.http_server import _protected_resource_doc

        doc = _protected_resource_doc(FAKE_PUBLIC_URL, FAKE_ISSUER)

        assert doc["authorization_servers"] == [FAKE_ISSUER]
        assert "mcp:read" in doc["scopes_supported"]
        assert "mcp:system" in doc["scopes_supported"]
        assert doc["bearer_methods_supported"] == ["header"]

    def test_protected_resource_doc_uses_public_url_as_resource(self):
        """OA-6: When public_url is set, it is used as the resource identifier."""
        from sp_mcp_server.http_server import _protected_resource_doc

        doc = _protected_resource_doc(FAKE_PUBLIC_URL, FAKE_ISSUER)
        assert doc["resource"] == FAKE_PUBLIC_URL

    def test_protected_resource_doc_falls_back_to_issuer(self):
        """OA-6: When public_url is empty, issuer is used as the resource identifier."""
        from sp_mcp_server.http_server import _protected_resource_doc

        doc = _protected_resource_doc("", FAKE_ISSUER)
        assert doc["resource"] == FAKE_ISSUER

    def test_unauthorized_includes_resource_metadata_uri_when_public_url_set(self):
        """OA-6: 401 WWW-Authenticate header contains resource_metadata URI."""
        from sp_mcp_server.http_server import OIDCBearerMiddleware
        from unittest.mock import MagicMock

        mw = OIDCBearerMiddleware.__new__(OIDCBearerMiddleware)
        mw.public_url = FAKE_PUBLIC_URL

        resp = mw._unauthorized("missing_token", "Bearer token required.")

        www_auth = resp.headers.get("WWW-Authenticate", "")
        assert "resource_metadata" in www_auth
        assert f"{FAKE_PUBLIC_URL}/.well-known/oauth-protected-resource" in www_auth

    def test_unauthorized_no_resource_metadata_when_public_url_absent(self):
        """OA-6: 401 WWW-Authenticate omits resource_metadata when public_url not set."""
        from sp_mcp_server.http_server import OIDCBearerMiddleware
        from unittest.mock import MagicMock

        mw = OIDCBearerMiddleware.__new__(OIDCBearerMiddleware)
        mw.public_url = ""

        resp = mw._unauthorized("missing_token", "Bearer token required.")

        www_auth = resp.headers.get("WWW-Authenticate", "")
        assert "resource_metadata" not in www_auth
        assert 'Bearer realm="sp-mcp-server"' in www_auth


# ---------------------------------------------------------------------------
# OA-7 — Auth model in ACTLOG DEFINE SCRATCHPADENTRY
# ---------------------------------------------------------------------------

class TestAuthModelAudit:
    """OA-7: authmodel= field included in ACTLOG DEFINE SCRATCHPADENTRY."""

    def _make_server(self):
        from sp_mcp_server.mcp_factory import create_mcp_server
        from sp_mcp_server.commands.system.admin import DeleteAdmin
        from tests.fixtures import make_config_with_cred, SP_OUTPUT_SESSION_STRICT_TLS13
        from unittest.mock import MagicMock
        import os

        cfg = make_config_with_cred()
        admc = MagicMock()
        admc.config = cfg
        # Return session-strict output so _validate_session_security passes
        admc.execute.return_value = (SP_OUTPUT_SESSION_STRICT_TLS13, "", 0)

        os.environ["SP_MCP_SKIP_SECURITY_CHECKS"] = "1"
        try:
            server = create_mcp_server(
                server_name="test-server",
                tool_classes=[DeleteAdmin],
                admc_cli=admc,
                config=cfg,
            )
        finally:
            del os.environ["SP_MCP_SKIP_SECURITY_CHECKS"]

        # Restore the mock so execute records DEFINE SCRATCHPADENTRY calls correctly
        admc.execute.return_value = ("ANR0000I OK", "", 0)
        return server, admc

    def test_local_authmodel_in_actlog(self):
        """OA-7: stdio path (no auth) → authmodel=local in ACTLOG record."""
        from mcp.types import CallToolRequest, CallToolRequestParams
        from sp_mcp_server.mcp_factory import current_auth_model
        from unittest.mock import patch
        from tests.fixtures import run_tool, ADMIN_NAME_OLD

        server, admc = self._make_server()
        handler = server.request_handlers[CallToolRequest]

        tok = current_auth_model.set("local")
        try:
            with patch("sp_mcp_server.commands.system.admin.DeleteAdmin.execute",
                       return_value="Admin deleted"):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin", arguments={"admin_name": ADMIN_NAME_OLD}
                    ),
                )
                run_tool(handler, req)
        finally:
            current_auth_model.reset(tok)

        scratchpad_calls = [
            c.args[0] for c in admc.execute.call_args_list
            if "DEFINE SCRATCHPADENTRY" in str(c)
        ]
        assert scratchpad_calls, "Expected DEFINE SCRATCHPADENTRY to be called"
        assert any("authmodel=local" in call for call in scratchpad_calls)

    def test_client_credentials_authmodel_in_actlog(self):
        """OA-7: client_credentials OIDC token → authmodel=client_credentials in ACTLOG."""
        from mcp.types import CallToolRequest, CallToolRequestParams
        from sp_mcp_server.mcp_factory import current_auth_model, current_audit_user
        from unittest.mock import patch
        from tests.fixtures import run_tool, ADMIN_NAME_OLD

        server, admc = self._make_server()
        handler = server.request_handlers[CallToolRequest]

        user_tok = current_audit_user.set("mcp-client")
        auth_tok = current_auth_model.set("client_credentials")
        try:
            with patch("sp_mcp_server.commands.system.admin.DeleteAdmin.execute",
                       return_value="Admin deleted"):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin", arguments={"admin_name": ADMIN_NAME_OLD}
                    ),
                )
                run_tool(handler, req)
        finally:
            current_auth_model.reset(auth_tok)
            current_audit_user.reset(user_tok)

        scratchpad_calls = [
            c.args[0] for c in admc.execute.call_args_list
            if "DEFINE SCRATCHPADENTRY" in str(c)
        ]
        assert scratchpad_calls, "Expected DEFINE SCRATCHPADENTRY to be called"
        assert any("authmodel=client_credentials" in call for call in scratchpad_calls)

    def test_oidc_bearer_authmodel_in_actlog(self):
        """OA-7: Authorization Code token → authmodel=oidc_bearer in ACTLOG."""
        from mcp.types import CallToolRequest, CallToolRequestParams
        from sp_mcp_server.mcp_factory import current_auth_model, current_audit_user
        from unittest.mock import patch
        from tests.fixtures import run_tool, ADMIN_NAME_OLD, AUDIT_USER

        server, admc = self._make_server()
        handler = server.request_handlers[CallToolRequest]

        user_tok = current_audit_user.set(AUDIT_USER)
        auth_tok = current_auth_model.set("oidc_bearer")
        try:
            with patch("sp_mcp_server.commands.system.admin.DeleteAdmin.execute",
                       return_value="Admin deleted"):
                req = CallToolRequest(
                    method="tools/call",
                    params=CallToolRequestParams(
                        name="delete_admin", arguments={"admin_name": ADMIN_NAME_OLD}
                    ),
                )
                run_tool(handler, req)
        finally:
            current_auth_model.reset(auth_tok)
            current_audit_user.reset(user_tok)

        scratchpad_calls = [
            c.args[0] for c in admc.execute.call_args_list
            if "DEFINE SCRATCHPADENTRY" in str(c)
        ]
        assert scratchpad_calls, "Expected DEFINE SCRATCHPADENTRY to be called"
        assert any("authmodel=oidc_bearer" in call for call in scratchpad_calls)

    def test_dynamic_session_authmodel_set_after_authenticate(self):
        """OA-7: authenticate_session sets current_auth_model to 'dynamic_session'."""
        from sp_mcp_server.mcp_factory import current_auth_model
        from sp_mcp_server.commands.system.auth import AuthenticateSession
        from unittest.mock import MagicMock
        from tests.fixtures import make_config_with_cred, SP_OUTPUT_QUERY_ADMIN_SYSTEM

        cfg = make_config_with_cred()
        admc = MagicMock()
        admc.config = cfg
        # execute_silent is called twice: QUERY STATUS (auth check) then QUERY ADMIN (privilege)
        admc.execute_silent.return_value = (SP_OUTPUT_QUERY_ADMIN_SYSTEM, "", 0)

        # BaseCommand.__init__ only accepts cli; config is not a parameter
        cmd = AuthenticateSession(cli=admc)
        cmd.execute({"username": "alice", "password": "pw"})

        assert current_auth_model.get() == "dynamic_session"
