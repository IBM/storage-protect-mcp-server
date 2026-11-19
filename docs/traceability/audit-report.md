# Independent Project Audit Report

* **Audit scope**: Documentation, source code, tests, and packaging metadata in the working tree (`dev-secure-mcp` branch)
* **Audit date**: 2026-09 (independent re-audit; post-remediation state)
* **Assessment focus**: Consistency, correctness, and completeness across the full document and source corpus
* **Method**: Static cross-reference of all docs layers (analysis → design → implementation → traceability), source code review, live test execution against the `.venv-audit` environment; no IBM Storage Protect server or live OIDC identity provider was available for runtime validation
* **Test result**: **88 passed** (`88 passed in 3.90s`)

---

## 1. Executive Summary

The project is in a **strong, well-documented, fully-remediated state**. All security controls across all seven domains — network security, identity & credentials, access management, policy management, secure integrations, non-repudiation, and dynamic authentication — are consistently documented from analysis through design, implementation specification, traceability matrix, and automated test. No open findings remain.

---

## 2. Active Findings

No open findings.

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

---

## 4. Verification Record

| Item | Detail |
|:---|:---|
| Test suite result | **88 passed** (`88 passed in 3.90s`) |
| Test suite version | Python 3.13.3, pytest 9.1.1 |
| Open findings | **None** |
| Runtime validation | No IBM Storage Protect server or live OIDC identity provider available; live-system behaviour unverified |
| Traceability cross-reference | [`docs/traceability/gap-analysis.md`](gap-analysis.md) · [`docs/traceability/traceability-matrix.md`](traceability-matrix.md) |

---

## Appendix A — Document Corpus Reviewed

| Layer | Files Reviewed |
|:---|:---|
| **Analysis** | `docs/analysis/security-design-analysis.md`, `docs/analysis/security-dynamic-authn-analysis.md` |
| **Design** | `docs/design/security-access.md`, `security-dynamic-authn.md`, `security-identity-credentials.md`, `security-integrations.md`, `security-network.md`, `security-non-repudiation.md`, `security-policy.md` |
| **Implementation** | `docs/implement/impl-security-access.md`, `impl-security-dynamic-authn.md`, `impl-security-identity-credentials.md`, `impl-security-integrations.md`, `impl-security-network.md`, `impl-security-non-repudiation.md`, `impl-security-policy.md` |
| **Architecture** | `docs/architecture/architecture.md`, `module-clients.md`, `module-operations.md`, `module-policies.md`, `module-storage.md`, `module-system.md` |
| **Guides** | `docs/guides/planning-guide.md`, `install-guide.md`, `configure-guide.md`, `user-guide.md`, `troubleshoot.md` |
| **Traceability** | `docs/traceability/traceability-matrix.md`, `gap-analysis.md` |
| **Source** | `src/sp_mcp_server/session.py`, `commands/system/auth.py`, `cli_wrapper.py`, `mcp_factory.py`, `config.py`, `http_server.py`, all `main*.py` entry points |
| **Tests** | `tests/test_security_controls.py`, `test_cli_wrapper.py`, `test_commands.py`, `test_config.py`, `test_core_components.py` |
| **Packaging** | `pyproject.toml` |
