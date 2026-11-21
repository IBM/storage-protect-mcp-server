"""
Security-control regression tests — OAuth2/OIDC dynamic authorization & session binding (OA-8 / INT-2 / DAUTH-11).

Controls covered:
  OA-8   Per-message SSE privilege & token expiration enforcement.
         Dynamic verification that tool execution gates inspect active SSESessionContext
         rather than stale task-local ContextVars from initial SSE connection.
  INT-2  OIDC bearer token validation, scope-to-privilege mapping, and call-time authorization.
  CWE-284 Authorization Bypass mitigation (privilege downgrade enforcement).
  CWE-613 Insufficient Session Expiration mitigation (dynamic call-time expiration check).
"""

import json
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import allure
import pytest
from starlette.testclient import TestClient

from mcp.types import CallToolRequest, CallToolRequestParams

from sp_mcp_server.http_server import (
    OIDCBearerMiddleware,
    SSESessionContext,
    create_http_app,
    get_sse_session_context,
    get_stream_owner,
    record_stream_owner,
    register_sse_session_context,
    remove_stream_owner,
    update_sse_session_context,
)
from sp_mcp_server.mcp_factory import (
    create_mcp_server,
    current_audit_user,
    current_connection_id,
    current_request_privilege,
    current_session_id,
    reset_execution_state,
)
from sp_mcp_server.commands.system.admin import DeleteAdmin
from sp_mcp_server.commands.system.server import QueryServerStatus
from tests.fixtures import (
    ADMIN_NAME_TARGET_NODE,
    SP_OUTPUT_PRIVILEGE_SYSTEM,
    SP_OUTPUT_SESSION_STRICT_TLS13,
    SP_OUTPUT_SCRATCHPAD_OK,
    first_text,
    make_config_with_cred,
    mock_admc,
    run_tool,
)


@pytest.fixture(autouse=True)
def clean_execution_state():
    """Ensure clean execution state and stream contexts between tests."""
    reset_execution_state()
    yield
    reset_execution_state()


@allure.epic("Security Architecture & Access Control")
@allure.feature("OAuth2 & SSE Per-Message Authorization (Control OA-8)")
class TestOAuth2SSESessionBinding:
    """Regression suite for Control OA-8 and INT-2."""

    @allure.story("OA-8 / SSESessionContext Registry")
    @allure.title("TC-OA8-00: Session context registration, canonical/hex lookup, and cleanup")
    @allure.severity(allure.severity_level.NORMAL)
    def test_sse_session_context_registration_and_lookup(self):
        """Verify registration, lookup, hex normalization, and removal of SSESessionContext."""
        stream_id = str(uuid.uuid4())
        now = time.time()
        ctx = register_sse_session_context(
            stream_id=stream_id,
            owner_sub="user_alice",
            privilege="system",
            exp=now + 3600,
            auth_model="oidc",
        )
        assert ctx is not None
        assert ctx.owner_sub == "user_alice"
        assert ctx.active_privilege == "system"
        assert ctx.active_exp == now + 3600

        # Verify lookup via canonical UUID string
        found = get_sse_session_context(stream_id)
        assert found is not None
        assert found.owner_sub == "user_alice"

        # Verify lookup via 32-char hex string (without hyphens)
        hex_id = stream_id.replace("-", "")
        found_hex = get_sse_session_context(hex_id)
        assert found_hex is not None
        assert found_hex.owner_sub == "user_alice"

        # Clean up
        remove_stream_owner(stream_id)
        assert get_sse_session_context(stream_id) is None
        assert get_sse_session_context(hex_id) is None
        assert get_stream_owner(stream_id) is None

    @allure.story("OA-8 / CWE-284 Privilege Downgrade Enforcement")
    @allure.title("TC-OA8-01: Reject privileged tool execution on SSE stream after privilege downgrade")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.issue("VUL0790479", "HackerOne Advisory: Stale SSE Session Privilege Retention")
    def test_sse_privilege_downgrade_rejected(self):
        """
        TC-OA8-01: Verify that lowering the privilege in SSESessionContext (e.g. from
        'system' to 'any') blocks subsequent execution of privileged tools on that stream.
        Mitigates CWE-284 (Authorization Bypass via Stale SSE Session Context).
        """
        cfg = make_config_with_cred()
        admc = mock_admc(stdout=SP_OUTPUT_SESSION_STRICT_TLS13, code=0)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[DeleteAdmin, QueryServerStatus],
            admc_cli=admc,
            config=cfg,
        )
        admc.execute.return_value = (SP_OUTPUT_SCRATCHPAD_OK, "", 0)

        stream_id = str(uuid.uuid4())
        now = time.time()

        # Step 1: Initial connection established under 'system' privilege
        register_sse_session_context(
            stream_id=stream_id,
            owner_sub="alice",
            privilege="system",
            exp=now + 3600,
            auth_model="oidc",
        )

        handler = server.request_handlers[CallToolRequest]
        current_connection_id.set(stream_id)

        try:
            # Step 2: Simulate subsequent message on stream arriving with downgraded privilege ('any')
            update_sse_session_context(
                stream_id=stream_id,
                privilege="any",
                exp=now + 3600,
                auth_model="oidc",
            )

            # Step 3: Invoke tool requiring 'system' privilege
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="delete_admin", arguments={"admin_name": ADMIN_NAME_TARGET_NODE}
                ),
            )
            res = run_tool(handler, req)

            # Step 4: Verify request is denied dynamically
            assert len(res.content) == 1
            payload = json.loads(first_text(res))
            assert payload.get("is_error") is True
            assert payload.get("error_type") == "AUTHORIZATION_DENIED"
            assert "OIDC token does not have the privilege required" in payload.get("message", "")
        finally:
            remove_stream_owner(stream_id)

    @allure.story("OA-8 / CWE-613 Call-Time Token Expiration")
    @allure.title("TC-OA8-02: Halt tool execution with AUTHENTICATION_REQUIRED when stream token expires")
    @allure.severity(allure.severity_level.CRITICAL)
    @allure.issue("VUL0790479", "HackerOne Advisory: Expired SSE Token Retention")
    def test_sse_expired_token_rejected(self):
        """
        TC-OA8-02: Verify that an expired token in SSESessionContext halts tool invocation
        with AUTHENTICATION_REQUIRED at call time.
        Mitigates CWE-613 (Insufficient Session Expiration).
        """
        cfg = make_config_with_cred()
        admc = mock_admc(stdout=SP_OUTPUT_SESSION_STRICT_TLS13, code=0)

        server = create_mcp_server(
            server_name="test-server",
            tool_classes=[QueryServerStatus],
            admc_cli=admc,
            config=cfg,
        )

        stream_id = str(uuid.uuid4())
        now = time.time()

        # Stream context initialized with token already expired 10 seconds ago
        register_sse_session_context(
            stream_id=stream_id,
            owner_sub="alice",
            privilege="any",
            exp=now - 10.0,
            auth_model="oidc",
        )

        handler = server.request_handlers[CallToolRequest]
        current_connection_id.set(stream_id)

        try:
            req = CallToolRequest(
                method="tools/call",
                params=CallToolRequestParams(
                    name="query_server_status", arguments={}
                ),
            )
            res = run_tool(handler, req)

            assert len(res.content) == 1
            payload = json.loads(first_text(res))
            assert payload.get("is_error") is True
            assert payload.get("error_type") == "AUTHENTICATION_REQUIRED"
            assert "expired" in payload.get("message", "").lower()
        finally:
            remove_stream_owner(stream_id)

    @allure.story("INT-2 / ASGI Standard Context")
    @allure.title("TC-OA8-03: OIDCBearerMiddleware populates ASGI scope['user'] and scope['state']")
    @allure.severity(allure.severity_level.NORMAL)
    def test_asgi_scope_user_populated(self):
        """
        TC-OA8-03: Verify that OIDCBearerMiddleware correctly populates ASGI scope['user']
        and scope['state'] with sub, privilege, exp, and auth_model.
        """
        captured_scope = {}

        async def dummy_app(scope, receive, send):
            captured_scope.update(scope)
            from starlette.responses import Response
            resp = Response("OK", status_code=200)
            await resp(scope, receive, send)

        async def mock_get_jwks(self):
            self._jwks_uri = "https://login.example.com/jwks"
            return {"keys": []}

        middleware = OIDCBearerMiddleware(
            dummy_app,
            issuer="https://login.example.com",
            audience="test-aud",
        )

        client = TestClient(middleware, raise_server_exceptions=False)
        test_exp = time.time() + 1800

        with patch.object(OIDCBearerMiddleware, "_get_jwks", mock_get_jwks):
            with patch("jwt.PyJWKClient.get_signing_key_from_jwt"):
                with patch("jwt.decode", return_value={
                    "sub": "alice_sub",
                    "scope": "mcp:operator",
                    "exp": test_exp,
                    "iat": time.time(),
                }):
                    resp = client.get(
                        "/mcp/test",
                        headers={"Authorization": "Bearer mock_valid_token"},
                    )

        assert resp.status_code == 200
        assert "user" in captured_scope
        user_info = captured_scope["user"]
        assert user_info["sub"] == "alice_sub"
        assert user_info["privilege"] == "operator"
        assert user_info["exp"] == test_exp
        assert user_info["auth_model"] == "oidc"

        assert captured_scope["state"]["mcp_subject"] == "alice_sub"
        assert captured_scope["state"]["mcp_privilege"] == "operator"
        assert captured_scope["state"]["mcp_exp"] == test_exp

    @allure.story("OA-8 / Live POST Context Synchronization")
    @allure.title("TC-OA8-04: Guarded POST synchronizes live SSESessionContext with incoming token claims")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_guarded_post_updates_sse_session_context(self):
        """
        TC-OA8-04: Verify that a valid POST to /mcp/messages updates the live
        SSESessionContext with incoming token's updated privilege and exp claims.
        """
        mock_server = MagicMock()
        app = create_http_app(mock_server, "https://login.example.com", "test-aud")

        async def mock_get_jwks(self):
            self._jwks_uri = "https://login.example.com/jwks"
            return {"keys": []}

        stream_uuid = uuid.UUID("11223344-5566-7788-99aa-bbccddeeff00")
        mock_writer = AsyncMock()

        mcp_mount = next(r for r in app.routes if getattr(r, "path", None) == "/mcp")
        msg_mount = next(r for r in mcp_mount.routes if getattr(r, "path", None) == "/messages")

        transport = None
        for cell in (msg_mount.app.__closure__ or []):
            if hasattr(cell.cell_contents, "_read_stream_writers"):
                transport = cell.cell_contents
                break

        assert transport is not None
        transport._read_stream_writers[stream_uuid] = mock_writer

        now = time.time()
        # Initial registration with 'operator' and 1 hour exp
        register_sse_session_context(
            stream_id=str(stream_uuid),
            owner_sub="alice_oidc_sub",
            privilege="operator",
            exp=now + 3600,
        )

        try:
            client = TestClient(app, raise_server_exceptions=False)
            updated_exp = now + 7200
            with patch.object(OIDCBearerMiddleware, "_get_jwks", mock_get_jwks):
                with patch("jwt.PyJWKClient.get_signing_key_from_jwt"):
                    with patch("jwt.decode", return_value={
                        "sub": "alice_oidc_sub",
                        "scope": "mcp:system",
                        "exp": updated_exp,
                        "iat": now,
                    }):
                        resp = client.post(
                            f"/mcp/messages?session_id={stream_uuid}",
                            headers={"Authorization": "Bearer alice_token_system"},
                            json={"jsonrpc": "2.0", "method": "tools/call", "params": {}, "id": 1},
                        )

            assert resp.status_code == 202
            # Context must now reflect escalated privilege and updated exp
            ctx = get_sse_session_context(str(stream_uuid))
            assert ctx is not None
            assert ctx.active_privilege == "system"
            assert ctx.active_exp == updated_exp
        finally:
            remove_stream_owner(str(stream_uuid))

    @allure.story("DAUTH-10 / Context Isolation")
    @allure.title("TC-OA8-05: Clean reset of all task-local execution ContextVars")
    @allure.severity(allure.severity_level.NORMAL)
    def test_reset_execution_state(self):
        """
        TC-OA8-05: Verify that reset_execution_state() cleans all contextvars.
        """
        current_session_id.set("test-sess")
        current_audit_user.set("test-user")
        current_request_privilege.set("system")
        current_connection_id.set("test-conn")

        reset_execution_state()

        assert current_session_id.get() is None
        assert current_audit_user.get() is None
        assert current_request_privilege.get() is None
        assert current_connection_id.get() is None
