# Implementation: Dynamic & Delegated User Authentication

* **Domain**: Identity, Credentials & Delegated Authentication
* **Revision**: 2026-11 (Multi-Client Transport Isolation & Anti-IDOR Enforcement — DAUTH-10, HackerOne #4212881 Remediation)
* **Status**: Fully implemented and regression-tested — challenge, bounded leases, authorization, delegated execution, subprocess assertions, credential-lifecycle zeroing, explicit logout, target-server binding, and multi-client transport isolation (DAUTH-10) all present
* **Analysis reference**: [`docs/analysis/security-dynamic-authn-analysis.md`](../analysis/security-dynamic-authn-analysis.md)
* **Design reference**: [`docs/design/security-dynamic-authn.md`](../design/security-dynamic-authn.md)
* **Cross-reference**: [`docs/implement/impl-security-identity-credentials.md`](impl-security-identity-credentials.md) · [`docs/implement/impl-security-integrations.md`](impl-security-integrations.md) · [`docs/implement/impl-security-non-repudiation.md`](impl-security-non-repudiation.md) · [`docs/implement/impl-security-access.md`](impl-security-access.md) · [`docs/implement/impl-security-policy.md`](impl-security-policy.md)
* **Files targeted**: `src/sp_mcp_server/session.py`, `src/sp_mcp_server/commands/system/auth.py`, `src/sp_mcp_server/mcp_factory.py`, `src/sp_mcp_server/cli_wrapper.py`

---

## 1. Overview

This document details the implementation architecture, data structures, and code-level specifications for **Dynamic & Delegated User Authentication (Challenge-Response)**. It bridges the gap between interactive LLM chat clients (which cannot hold static credentials) and IBM Storage Protect server instances.

---

## 2. Component Architecture

The dynamic authentication subsystem currently consists of three components:

1. **`SessionManager` (`src/sp_mcp_server/session.py`)**:
   Stores synchronized in-memory ephemeral session leases with bounded sliding inactivity expiration. Cleanup is performed during session creation and explicit cleanup calls.
2. **`authenticate_session` Tool (`src/sp_mcp_server/commands/system/auth.py`)**:
   Verifies supplied credentials via zero-trace `execute_silent()` and provisions a bounded lease containing the username, password, and parsed privilege classes for delegated execution.
3. **`logout_session` Tool (`src/sp_mcp_server/commands/system/auth.py`)**:
   Explicitly revokes an active session lease, zeros `SessionLease.password`, and clears `current_session_id` / `current_audit_user` context variables. Available at `required_privilege: any` (AUD-08).
4. **Session Interceptor Hook (`src/sp_mcp_server/mcp_factory.py`)**:
   Checks whether dynamic auth is enabled, validates the active session privilege, invokes `_check_session_target_server()` to enforce cross-server isolation (DAUTH-7), and applies the session execution context before executing commands.

```mermaid
flowchart LR
    A[MCP Tool Request] --> B[mcp_factory.handle_call_tool]
    B --> C{SP_MCP_AUTH_MODE == dynamic?}
    C -- No (Service Account) --> D[Static registration gate + configured credential]
    C -- Yes --> E{Active Session Token?}
    E -- No --> F[Return AUTHENTICATION_REQUIRED challenge]
    E -- Yes --> G[Refresh lease + set current_audit_user]
    G --> H[Enforce session privilege]
    H --> I[_check_session_target_server — DAUTH-7]
    I --> J[Execute with delegated session credentials]
```

---

## 3. Data Structures & Schemas

### 3.1 Ephemeral Session Lease Record

The actual `SessionLease` dataclass (as implemented in [`session.py`](../../src/sp_mcp_server/session.py)) includes `password` for delegated command execution and `target_server` for future server-binding enforcement:

```python
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional, Set

@dataclass
class SessionLease:
    session_id: str
    username: str
    privilege_classes: Set[str]
    oidc_subject: Optional[str] = None          # Bound OIDC 'sub' claim (DAUTH-10)
    connection_id: Optional[str] = None         # Bound transport connection / SSE session (DAUTH-10)
    transport_mode: str = "http"                # 'stdio' or 'http' (DAUTH-10)
    password: Optional[str] = None          # Retained for delegated execution; see AUD-02 / AUD-08
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    last_accessed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    ttl_seconds: int = DEFAULT_SESSION_TTL_SECONDS
    target_server: Optional[str] = None     # Enforced in mcp_factory._check_session_target_server() — DAUTH-7

    def is_expired(self) -> bool:
        """Check inactivity TTL and absolute MAX_SESSION_TTL_SECONDS."""
        now = datetime.now(timezone.utc)
        inactive_seconds = (now - self.last_accessed_at).total_seconds()
        total_seconds = (now - self.created_at).total_seconds()
        return inactive_seconds > self.ttl_seconds or total_seconds > MAX_SESSION_TTL_SECONDS

    def touch(self) -> None:
        self.last_accessed_at = datetime.now(timezone.utc)
```

> **AUD-08 (closed):** `password` is zeroed (`None`) on every removal path — `revoke_session()`, expiry in `get_session()`, `cleanup_expired()`, and `clear()`. The `logout_session` tool triggers `revoke_session()` for user-initiated revocation.

### 3.2 Standard Challenge Response Payload

When no session exists, the interceptor produces an error payload formatted in JSON:

```python
AUTHENTICATION_REQUIRED_PAYLOAD = {
    "is_error": True,
    "error_type": "AUTHENTICATION_REQUIRED",
    "message": "Authentication required. Please provide your IBM Storage Protect administrator credentials.",
    "challenge": {
        "required_fields": ["username", "password"],
        "supported_schemes": ["basic_delegated", "oidc_bearer"],
        "auth_tool": "authenticate_session"
    }
}
```

---

## 4. Code Specifications

### 4.1 Zero-Trace Authentication in `authenticate_session`

The authentication tool performs zero-trace validation against `dsmadmc`. `execute_silent()` returns `(stdout, stderr, return_code)`:

```python
# execute_silent return order: (stdout, stderr, return_code)
stdout, stderr, ret_code = self.cli.execute_silent(
    command="QUERY STATUS",
    admin_id=username,
    password=password,
)

if ret_code != 0:
    return json.dumps({
        "success": False,
        "error": "Authentication failed: invalid administrator credentials.",
        "returncode": ret_code,
        "details": (stderr or stdout or "Access denied").strip(),
    }, indent=2)

# Query admin authority level to establish privilege bounds
priv_out, _, _ = self.cli.execute_silent(
    command=f"QUERY ADMIN {username} FORMAT=DETAILED",
    admin_id=username,
    password=password,
)

privileges = _parse_privileges(priv_out)

# Mint session lease (bound to caller connection & OIDC subject — DAUTH-10)
conn_id = current_connection_id.get()
current_sub = current_oidc_subject.get() or current_audit_user.get()
transport_mode = "http" if conn_id or current_oidc_subject.get() else "stdio"
bound_conn_id = conn_id or ("stdio" if transport_mode == "stdio" else None)

lease = global_session_manager.create_session(
    username=username,
    privileges=privileges,
    target_server=target_server,
    password=password,
    oidc_subject=current_sub if current_oidc_subject.get() else None,
    connection_id=bound_conn_id,
    transport_mode=transport_mode,
)

# Set identity context for audit & forensics
if not current_oidc_subject.get():
    current_audit_user.set(username)
current_session_id.set(lease.session_id)
current_auth_model.set("dynamic_session")   # OA-7
```

> **AUD-09 (corrected):** The return order is `(stdout, stderr, return_code)` — corrected from the earlier `(return_code, stdout, stderr)` example in the original document.

---

## 5. Security & Operational Hardening

1. **Sliding Window Inactivity Timeout**:
   * Default timeout: **15 minutes** (`SP_MCP_SESSION_TTL=900`); absolute max **60 minutes** (`SP_MCP_SESSION_MAX_TTL=3600`).
   * Cleanup is opportunistic — triggered during `create_session()` and explicit `cleanup_expired()` calls; operators of long-lived processes should schedule periodic cleanup or rely on `SP_MCP_SESSION_MAX_TTL` to bound lease lifetimes.

2. **Credential Lifecycle (AUD-08)**:
   * `SessionLease.password` is set to `None` on every removal path: `revoke_session()`, expiry in `get_session()`, `cleanup_expired()`, and `clear()` at shutdown.
   * The `logout_session` tool calls `revoke_session()`, clears `current_session_id` / `current_audit_user`, and returns a JSON confirmation.

3. **Target-Server Binding (DAUTH-7)**:
   * `_check_session_target_server(session, config)` in `mcp_factory.py` returns an error string if `session.target_server` is set and does not match `config.server_address`.
   * Single-server deployments (no `target_server` on the lease) skip the check — fully backward-compatible.

4. **Identity Context Propagation (NR-1)**:
   * When `authenticate_session` succeeds, `current_audit_user` is set to the validated username.
   * Subsequent write executions propagate that username to the IBM Storage Protect Activity Log and execute through the active session credential context.

5. **Memory Safety & Zero-Trace**:
   * Plaintext passwords received in `authenticate_session` exist only within local stack frames and are zeroed from the session store on the first removal operation.
   * Credential verification commands are strictly routed through `execute_silent()`.

6. **Multi-Client Transport Isolation & Anti-IDOR (DAUTH-10)**:
   * **Module-Level Globals Eliminated**: Module-level variables `_process_session_id` and `_process_audit_user` are eliminated.
   * **Session Resolution Hierarchy**: Tool interception in `mcp_factory.py` resolves candidate session IDs from request ContextVars (`current_session_id`) and connection mappings first.
   * **Anti-IDOR Ownership Verification**: If caller passes explicit `_session_id`, the server validates `session.oidc_subject == current_sub`. Mismatched ownership or cross-realm redemption (e.g. attempting to redeem a stdio lease over HTTP) returns `AUTHORIZATION_DENIED`.
   * **Compound Dual-Identity Logging**: Mutating commands emit both `oidc_user` and `sp_admin` to SP ACTLOG (`DEFINE SCRATCHPADENTRY MCP_AUDIT oidc_user=<sub|local> sp_admin=<admin_name> ...`), maintaining non-repudiation (NR-1 / POL-4).
   * **Protected Revocation**: `logout_session` verifies that the caller owns the targeted session before calling `revoke_session()`.
   * **SSE URL Advertisement**: In `http_server.py`, `SseServerTransport("messages")` registers relative to the `/mcp` mount, avoiding route doubling.

7. **SSE Stream Ownership Gate (`http_server.py`)**:
   * To prevent stream hijacking in asynchronous AnyIO task queues, `http_server.py` maintains `_sse_stream_owners: Dict[str, str]` mapping active stream UUIDs to creator OIDC subjects.
   * Incoming `POST /mcp/messages?session_id=...` requests are verified against `_sse_stream_owners`. If the POST caller's OIDC subject does not match the registering stream owner, the endpoint immediately returns **HTTP 403 Forbidden** with JSON-RPC error `-32001`.

8. **Stdio Lease Lifecycle & Reverse Resolution (`session.py` / `mcp_factory.py`)**:
   * Single-client stdio mode maps connection ID to `"stdio"`. In `session.py`, `get_session_id_for_connection()` traverses `reversed(list(self._sessions.items()))` so that newly created leases immediately supersede older leases upon re-authentication, preventing FIFO dictionary iteration shadowing.
   * In `mcp_factory.py`, fallback to `"stdio"` is strictly restricted to `transport_mode == "stdio"`. Network HTTP requests without an OIDC subject are blocked from inheriting local stdio administrator credentials.

---

## 6. Testing & Validation Plan

| Test Case | Objective | Status |
|:---|:---|:---|
| `TestDynamicAuthentication::test_dynamic_auth_challenge_when_unauthenticated` | Tool calls without active session yield `AUTHENTICATION_REQUIRED` | ✅ |
| `TestDynamicAuthentication::test_authenticate_session_tool_valid_credentials` | Valid credentials create lease and set privilege context | ✅ |
| `TestDynamicAuthentication::test_authenticate_session_tool_invalid_credentials` | Invalid password returns structured failure response | ✅ |
| `TestDynamicAuthentication::test_session_ttl_is_bounded` | TTL capped at `MAX_SESSION_TTL_SECONDS` on create | ✅ |
| `TestDynamicAuthentication::test_dynamic_auth_denies_insufficient_privilege` | `{"any"}`-privilege session denied from `system`-privilege tool | ✅ |
| `TestDynamicAuthentication::test_dynamic_auth_executes_when_session_authenticated` | Tool executes; `current_audit_user` set from session username | ✅ |
| `TestDelegatedSubprocess::test_delegated_credentials_passed_to_subprocess` | `-ID=` and `-PA=` appear in `subprocess.run` call when `current_execution_credentials` set | ✅ |
| `TestDelegatedSubprocess::test_execution_credentials_cleared_after_tool_call` | `current_execution_credentials` is `None` after success and exception paths | ✅ |
| `TestOIDCAuthorization::test_oidc_scope_system_allows_system_tool` | `mcp:system` token allows `system`-privilege tool | ✅ |
| `TestOIDCAuthorization::test_oidc_scope_read_denies_write_tool` | `mcp:read` token denies `system`-privilege tool with `AUTHORIZATION_DENIED` | ✅ |
| `TestOIDCAuthorization::test_oidc_unknown_scope_treated_as_any` | Unknown scope resolves to `any` privilege | ✅ |
| `TestEntryPointStartup::test_all_main_entry_points_use_secure_startup` | All `main*.py` entry points call `secure_startup()` | ✅ |
| `TestSessionCredentialLifecycle::test_password_zeroed_on_revoke` | `SessionLease.password` is `None` after `revoke_session()` (AUD-08) | ✅ |
| `TestSessionCredentialLifecycle::test_password_zeroed_on_expiry_in_get_session` | `password` zeroed when expiry detected in `get_session()` (AUD-08) | ✅ |
| `TestSessionCredentialLifecycle::test_password_zeroed_on_cleanup_expired` | `password` zeroed in bulk `cleanup_expired()` sweep (AUD-08) | ✅ |
| `TestSessionCredentialLifecycle::test_password_zeroed_on_clear` | `password` zeroed on `clear()` / shutdown (AUD-08) | ✅ |
| `TestSessionCredentialLifecycle::test_logout_session_revokes_and_clears_credential` | `logout_session` revokes lease and confirms credential cleared (AUD-08) | ✅ |
| `TestSessionCredentialLifecycle::test_logout_session_no_active_session` | `logout_session` with no session returns graceful failure | ✅ |
| `TestSessionCredentialLifecycle::test_logout_session_explicit_session_id` | `logout_session` with explicit `session_id` parameter revokes correct lease | ✅ |
| `TestTargetServerBinding::test_cross_server_session_is_denied` | Mismatched `target_server` → `AUTHORIZATION_DENIED` with both server names (DAUTH-7) | ✅ |
| `TestTargetServerBinding::test_matching_target_server_is_allowed` | Matching `target_server` → command executes (DAUTH-7) | ✅ |
| `TestTargetServerBinding::test_no_target_server_on_session_is_allowed` | `target_server=None` → check skipped, command executes (DAUTH-7) | ✅ |
| `TestTargetServerBinding::test_check_session_target_server_helper_*` | Unit tests for `_check_session_target_server()` helper (3 paths) (DAUTH-7) | ✅ |
| `TestMultiClientDynamicAuthIsolation::test_cross_client_session_bleed_denied` | Client B cannot inherit Client A's session in the same process (DAUTH-10) | ✅ |
| `TestMultiClientDynamicAuthIsolation::test_explicit_session_id_idor_rejected` | Supplying another client's explicit `_session_id` returns `AUTHORIZATION_DENIED` (DAUTH-10) | ✅ |
| `TestMultiClientDynamicAuthIsolation::test_logout_does_not_terminate_other_client_sessions` | Client B logout does not disrupt Client A's active session (DAUTH-10) | ✅ |
| `TestMultiClientDynamicAuthIsolation::test_dual_audit_attribution_logged` | POL-4 audit logs record both OIDC `sub` and SP admin username (DAUTH-10) | ✅ |
| `TestMultiClientDynamicAuthIsolation::test_sse_endpoint_advertisement_correct` | SSE endpoint advertises `/mcp/messages` without path duplication (DAUTH-10) | ✅ |
| `TestMultiClientDynamicAuthIsolation::test_sse_stream_post_cross_client_rejected_403` | Cross-client POST to another user's SSE stream rejected with HTTP 403 (DAUTH-10, TC-DAUTH-29) | Planned |
| `TestMultiClientDynamicAuthIsolation::test_stdio_reauthentication_newest_lease_wins` | Re-authenticating in stdio supersedes previous lease via LIFO lookup (DAUTH-10, TC-DAUTH-30) | Planned |
| `TestMultiClientDynamicAuthIsolation::test_http_cannot_redeem_stdio_lease_via_idor` | Redeeming a stdio session lease over HTTP returns `AUTHORIZATION_DENIED` (DAUTH-10, TC-DAUTH-31) | Planned |
| `TestMultiClientDynamicAuthIsolation::test_unauthenticated_http_does_not_inherit_stdio_lease` | HTTP request without OIDC token does not fall back to stdio lease (DAUTH-10, TC-DAUTH-32) | Planned |

---

## 7. Cross-References

* Design Spec: [`docs/design/security-dynamic-authn.md`](../design/security-dynamic-authn.md)
* Analysis: [`docs/analysis/security-dynamic-authn-analysis.md`](../analysis/security-dynamic-authn-analysis.md)
* Identity & Credentials Implementation: [`docs/implement/impl-security-identity-credentials.md`](impl-security-identity-credentials.md)
* Integrations Implementation: [`docs/implement/impl-security-integrations.md`](impl-security-integrations.md)
* Non-Repudiation Implementation: [`docs/implement/impl-security-non-repudiation.md`](impl-security-non-repudiation.md)
* Access Management Implementation: [`docs/implement/impl-security-access.md`](impl-security-access.md)
* Policy Management Implementation: [`docs/implement/impl-security-policy.md`](impl-security-policy.md)
* Traceability Matrix: [`docs/traceability/traceability-matrix.md`](../traceability/traceability-matrix.md)
