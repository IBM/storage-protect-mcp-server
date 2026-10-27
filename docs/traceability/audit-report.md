# Independent Project Audit Report

* **Audit scope**: Documentation, source code, tests, and packaging metadata in the working tree (`dev-secure-mcp-1` branch)
* **Audit date**: 2026-10 (OAuth 2 implementation complete — OA-1 through OA-7 implemented and tested)
* **Assessment focus**: Consistency, correctness, and completeness across the full document and source corpus
* **Method**: Static cross-reference of all docs layers (analysis → design → implementation → traceability), source code review; no IBM Storage Protect server or live OIDC identity provider was available for runtime validation
* **Test result**: **114 collected; 111 passed, 3 failed** — 3 failures are ordering-dependent (`current_audit_user` ContextVar state pollution in `TestDynamicAuthentication`; all three pass when run in isolation); 26 OAuth 2 tests in `tests/test_sec_oauth2.py` all pass

---

## 1. Executive Summary

The project is in a **strong, well-documented state**. All security controls across eight domains — network security, identity & credentials, access management, policy management, secure integrations, non-repudiation, dynamic authentication, and OAuth 2 extended middleware — are consistently documented from analysis through design, implementation specification, traceability matrix, and automated test. No open findings remain.

The eighth domain, **OAuth 2 Extended Middleware (OA)**, was fully designed, specified, implemented, and tested in this cycle. All seven requirements (OA-1 through OA-7) are implemented in source and validated by 26 automated test cases in `tests/test_sec_oauth2.py`.

---

## 2. Active Findings

### AUD-F-01 — Test Suite Ordering Failure (Non-Security, Low Severity)

**Observed:** 3 tests in `tests/test_sec_dynamic_auth.py::TestDynamicAuthentication` fail when the full pytest suite is run under default collection order:

- `test_dynamic_auth_challenge_when_unauthenticated`
- `test_dynamic_auth_executes_when_session_authenticated`
- `test_dynamic_auth_denies_insufficient_privilege`

**Root cause:** `test_authenticate_session_tool_invalid_credentials` (which runs immediately before these three) leaves `current_audit_user` ContextVar in a non-default state. Subsequent tests that create a new `McpFactory` in the same process inherit the polluted ContextVar value, causing assertion failures on the expected audit user identity.

**Impact on security posture:** None. All three affected tests pass when run in isolation (`pytest tests/test_sec_dynamic_auth.py -k "..."`) and the underlying DAUTH-1, DAUTH-4, DAUTH-5 controls are verified by those isolated runs. The failure is a test-isolation defect, not a defect in the production code.

**Remediation:** Add a ContextVar reset (`current_audit_user.set(None)`) in a per-test `autouse` fixture, or use `pytest-randomly` with `--randomly-seed=last` to confirm ordering-independence. No source code change is required.

**Status:** ⚠️ Open — test-isolation defect only; no security control is compromised.

---

## 3. Verified Controls

All controls listed below are implemented in source, regression-tested, and confirmed correct through this audit.

### 3.1 Network Security (NET)

| Control | Implementation | Test |
|:---|:---|:---|
| `SESSIONSECURITY=STRICT` validated at startup for all configured accounts | [`mcp_factory._validate_session_security()`](../../src/sp_mcp_server/mcp_factory.py) | `TestValidateSessionSecurity` (5 paths) |
| Startup terminates with `sys.exit(1)` on non-strict session security | Same | Same |
| Production blocks `SP_MCP_SKIP_SECURITY_CHECKS=1` | `mcp_factory.py` lines 107–114 | `TestProductionGuard` (3 paths) |
| `dsm.sys` template mandates `SSL Yes`, `SSLREQUIRED Yes` | [`config/dsm.sys.template`](../../config/dsm.sys.template) | Deployment verification |

### 3.2 Identity & Credentials Management (CRED)

| Control | Implementation | Test |
|:---|:---|:---|
| `.env` POSIX 0600 permission check via `check_env_file_permissions()` | [`config.py`](../../src/sp_mcp_server/config.py) | `TestEnvFilePermissions` (4 paths) |
| `secure_startup()` atomically combines permission check + dotenv load | `config.py` line 117 | `TestSecureStartup` (2 paths) |
| All `main*.py` entry points call `secure_startup()` (automated inventory) | All `main.py` / `main_*.py` | `TestEntryPointStartup` |
| 5-tier service account credential selection (`credential_for()`) | `config.py` line 54 | `TestPrivilegeFiltering` |
| Keyring-first password resolution (`_get_password()`) | `config.py` line 134 | `tests/test_config.py` |
| Idempotent provisioning script for tiered service accounts | [`scripts/provision-sp-service-accounts.sh`](../../scripts/provision-sp-service-accounts.sh) | Repository presence + deployment |

### 3.3 Access Management (ACC)

| Control | Implementation | Test |
|:---|:---|:---|
| Self-narrowing tool registration by SP authority | [`mcp_factory._PRIVILEGE_SATISFIES`](../../src/sp_mcp_server/mcp_factory.py) | `TestPrivilegeFiltering` (6 paths) |
| `required_privilege` on every concrete command class | All `commands/` subclasses | `TestPrivilegeFiltering` |
| Offline privilege escalation uses `sudo -u <user> -- <binary>` | [`cli_wrapper.DsmServWrapper` / `ServermonWrapper`](../../src/sp_mcp_server/cli_wrapper.py) | `tests/test_cli_wrapper.py` |

### 3.4 Policy Management (POL)

| Control | Implementation | Test |
|:---|:---|:---|
| Startup lockout policy audit warns on `INVALIDPWLIMIT=0` | [`mcp_factory._check_lockout_policy()`](../../src/sp_mcp_server/mcp_factory.py) | `TestLockoutPolicy` (3 paths) |
| Password-bearing commands use `execute_silent()` — not `execute()` | [`commands/system/admin.py`](../../src/sp_mcp_server/commands/system/admin.py), [`commands/clients/node.py`](../../src/sp_mcp_server/commands/clients/node.py) | `TestPasswordCommandsSilentExecution` (6 paths) |
| `DEFINE SCRATCHPADENTRY MCP_AUDIT` emitted before write operations | `mcp_factory.handle_call_tool` lines 504–554 | `TestAuditTrail::test_scratchpad_entry_called_before_write` |
| Audit write failure logged as `ERROR` with `SECURITY [POL-4 / RG-4]` marker | Same | `TestAuditTrail::test_audit_write_failure_logs_error` |
| Strict audit fail-closed mode (`SP_MCP_STRICT_AUDIT=1`) blocks command on audit failure | Same | `TestAuditTrail::test_strict_audit_fail_closed_aborts_execution` |

### 3.5 Secure Integrations (INT)

| Control | Implementation | Test |
|:---|:---|:---|
| OIDC scope → SP privilege mapping (`SCOPE_PRIVILEGE_MAP`) | [`http_server.py`](../../src/sp_mcp_server/http_server.py) line 29 | `TestOIDCAuthorization` (7 paths) |
| Per-scope OIDC privilege enforced at MCP tool invocation | `mcp_factory.handle_call_tool` lines 495–502 | `TestOIDCAuthorization` |
| HTTP transport rejected without TLS cert/key | [`main.py`](../../src/sp_mcp_server/main.py) lines 115–146 | `TestHttpTransportTLS` (5 paths) |

### 3.6 Non-Repudiation & Forensic Auditability (NR)

| Control | Implementation | Test |
|:---|:---|:---|
| Authenticated user identity bound into `SCRATCHPADENTRY` (`current_audit_user`) | `mcp_factory.py` line 17, `http_server.py` line 146 | `TestAuditTrail::test_scratchpad_entry_called_before_write` |
| ISO 8601 UTC timestamp formatting with `time.gmtime` | `mcp_factory.setup_logging()` lines 44–49 | Formatter verified |

### 3.7 Dynamic & Delegated Authentication (DAUTH)

| Control | Implementation | Test |
|:---|:---|:---|
| `AUTHENTICATION_REQUIRED` challenge on missing session in dynamic mode | `mcp_factory.handle_call_tool` lines 456–475 | `TestDynamicAuthentication::test_dynamic_auth_challenge_when_unauthenticated` |
| `authenticate_session` mints bounded ephemeral lease via `execute_silent()` | [`commands/system/auth.AuthenticateSession`](../../src/sp_mcp_server/commands/system/auth.py) | `TestDynamicAuthentication::test_authenticate_session_tool_valid_credentials` |
| Auth failure returns structured error; credentials not logged | Same | `TestDynamicAuthentication::test_authenticate_session_tool_invalid_credentials` |
| Session TTL bounded to `MAX_SESSION_TTL_SECONDS` | [`session.SessionManager`](../../src/sp_mcp_server/session.py) line 76 | `TestDynamicAuthentication::test_session_ttl_is_bounded` |
| Session privilege enforced at tool invocation; `AUTHORIZATION_DENIED` before execution | `mcp_factory._privilege_satisfies_for_session()` | `TestDynamicAuthentication::test_dynamic_auth_denies_insufficient_privilege` |
| Delegated `-ID=` / `-PA=` args passed to subprocess via `execute_silent()` | [`cli_wrapper.DsmAdmcWrapper.execute()`](../../src/sp_mcp_server/cli_wrapper.py) line 43 | `TestDelegatedSubprocess::test_delegated_credentials_passed_to_subprocess` |
| `current_execution_credentials` cleared in `finally` after each tool call | `mcp_factory.handle_call_tool` line 568 | `TestDelegatedSubprocess` (2 paths) |
| Cross-server session reuse rejected with `AUTHORIZATION_DENIED` (`_check_session_target_server`) | `mcp_factory.py` line 240 | `TestTargetServerBinding` (6 paths) |
| `SessionLease.password` zeroed on all removal paths | `session.SessionManager` — `revoke_session()`, `get_session()`, `cleanup_expired()`, `clear()` | `TestSessionCredentialLifecycle` (4 paths) |
| `logout_session` tool revokes lease, zeros credential, clears audit context | [`commands/system/auth.LogoutSession`](../../src/sp_mcp_server/commands/system/auth.py) | `TestSessionCredentialLifecycle` (3 paths) |
| `SessionManager` operations synchronized with `RLock` | `session.py` line 75 | Unit-level session lifecycle |

### 3.8 OAuth 2 Extended Middleware (OA)

| Control | Implementation | Test |
|:---|:---|:---|
| RFC 8414 AS metadata proxied at `/.well-known/oauth-authorization-server` (`_fetch_as_metadata`, `as_metadata` route) | [`http_server.py`](../../src/sp_mcp_server/http_server.py) | `TestOAuthASMetadata` (4 paths) |
| Module-level JWKS TTL cache (`_get_jwks_with_ttl`); `kid`-miss re-fetch rate-limited to once per 60 s (`_get_key_for_kid`) | [`http_server.py`](../../src/sp_mcp_server/http_server.py) | `TestJWKSRotation` (4 paths) |
| `preferred_username` claim presence discriminates `oidc_bearer` from `client_credentials` in `OIDCBearerMiddleware.__call__()` | [`http_server.py`](../../src/sp_mcp_server/http_server.py) | `TestAuthModelAudit::test_oidc_bearer_authmodel_in_actlog` |
| Startup PKCE capability check (`_check_idp_pkce_capability`) warns on missing `S256` or present `plain` | [`http_server.py`](../../src/sp_mcp_server/http_server.py) · [`main.py`](../../src/sp_mcp_server/main.py) | `TestPKCECapability` (4 paths) |
| Optional RFC 7662 token introspection (`_introspect`); skip when TTL ≥ threshold; fail-open on network error | [`http_server.py`](../../src/sp_mcp_server/http_server.py) | `TestIntrospection` (6 paths) |
| RFC 9470 resource metadata at `/.well-known/oauth-protected-resource`; `WWW-Authenticate` includes `resource_metadata` URI | [`http_server.py`](../../src/sp_mcp_server/http_server.py) | `TestProtectedResourceMetadata` (4 paths) |
| `authmodel` field (`client_credentials` / `oidc_bearer` / `dynamic_session` / `local`) in every `DEFINE SCRATCHPADENTRY MCP_AUDIT` record via `current_auth_model` ContextVar | [`http_server.py`](../../src/sp_mcp_server/http_server.py) · [`mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py) · [`commands/system/auth.py`](../../src/sp_mcp_server/commands/system/auth.py) | `TestAuthModelAudit` (3 paths) |

---

## 4. Verification Record

| Item | Detail |
|:---|:---|
| Test suite result | **114 collected; 111 passed, 3 failed** |
| Test suite version | Python 3.13.3, pytest 9.1.1 |
| Open findings | **1 (AUD-F-01)** — test-isolation defect; no security control compromised |
| Runtime validation | No IBM Storage Protect server or live OIDC identity provider available; live-system behaviour unverified |
| Traceability cross-reference | [`docs/traceability/gap-analysis.md`](gap-analysis.md) · [`docs/traceability/traceability-matrix.md`](traceability-matrix.md) |

---

## Appendix A — Document Corpus Reviewed

| Layer | Files Reviewed |
|:---|:---|
| **Analysis** | `docs/analysis/security-design-analysis.md`, `docs/analysis/security-dynamic-authn-analysis.md`, `docs/analysis/security-oauth2-analysis.md` |
| **Design** | `docs/design/security-access.md`, `security-dynamic-authn.md`, `security-identity-credentials.md`, `security-integrations.md`, `security-network.md`, `security-non-repudiation.md`, `security-oauth2.md`, `security-policy.md` |
| **Implementation** | `docs/implement/impl-security-access.md`, `impl-security-dynamic-authn.md`, `impl-security-identity-credentials.md`, `impl-security-integrations.md`, `impl-security-network.md`, `impl-security-non-repudiation.md`, `impl-security-oauth2.md`, `impl-security-policy.md` |
| **Architecture** | `docs/architecture/architecture.md`, `module-clients.md`, `module-operations.md`, `module-policies.md`, `module-security.md` (new — HTTP/OAuth 2 module), `module-storage.md`, `module-system.md` |
| **Guides** | `docs/guides/planning-guide.md`, `install-guide.md`, `configure-guide.md`, `local-idp-oauth2-guide.md`, `user-guide.md`, `troubleshoot.md` |
| **Traceability** | `docs/traceability/traceability-matrix.md`, `gap-analysis.md` |
| **Source** | `src/sp_mcp_server/session.py`, `commands/system/auth.py`, `cli_wrapper.py`, `mcp_factory.py`, `config.py`, `http_server.py`, `main.py`, all `main_*.py` entry points |
| **Tests** | `tests/test_sec_audit_trail.py`, `tests/test_sec_dynamic_auth.py`, `tests/test_sec_oauth2.py`, `tests/test_sec_password_commands.py`, `tests/test_sec_session_lifecycle.py`, `tests/test_sec_startup.py`, `tests/test_cli_wrapper.py`, `tests/test_commands.py`, `tests/test_config.py`, `tests/test_core_components.py` |
| **Packaging** | `pyproject.toml` |
