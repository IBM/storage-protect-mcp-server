# IBM Storage Protect MCP Server — Gap Analysis

* **Revision**: 2026-09 (Post-Audit Remediation — AUD-07, AUD-08, DAUTH-7 Closed)
* **Cross-reference**: [`docs/traceability/traceability-matrix.md`](traceability-matrix.md) · [`docs/analysis/security-design-analysis.md`](../analysis/security-design-analysis.md) · [`docs/traceability/audit-report.md`](audit-report.md)
* **Source reference**: `src/sp_mcp_server/` · `tests/`

---

## 1. Executive Summary

All audit findings have been remediated. All 20 historical security gaps, 7 post-implementation residual gaps (RG-1 through RG-7), 5 Non-Repudiation gaps (NR-1 through NR-5), and all Dynamic Authentication (DAUTH) items are now closed.

Post-remediation additions: CRED-5 (idempotent SP service account provisioning script — AUD-07), DAUTH-8 (credential lifecycle zeroing on all removal paths — AUD-08), and DAUTH-9 (`logout_session` explicit revocation tool — AUD-08). DAUTH-7 (target-server binding) is fully implemented via `_check_session_target_server()` in `mcp_factory.py` and covered by 6 regression tests.

**Test suite total: 88 passing** (75 at prior revision; +7 AUD-08 credential-lifecycle tests, +6 DAUTH-7 target-server binding tests).

**No open items remain.**

---

## 2. Active Security Posture & Gap Status by Domain

| Security Domain | Requirements | Resolved / Closed | Open Gaps | Current Posture Status |
| :--- | :---: | :---: | :---: | :---: |
| **1. Network Security** | 3 | 3 | **0** | ✅ Fully Compliant (`SESSIONSECURITY=STRICT`, TLS 1.2/1.3, SSH Key Auth) |
| **2. Identity & Credentials** | 6 | 6 | **0** | ✅ Fully Compliant (5-Tier Credentials, Stash Auth, POSIX 0600 `.env` Check, Provisioning Script) |
| **3. Access Management** | 4 | 4 | **0** | ✅ Fully Compliant (Privilege Gate, Self-Narrowing Registry, Sudoers Execution) |
| **4. Policy Management** | 4 | 4 | **0** | ✅ Fully Compliant (Command Approval, `MINPWLENGTH` Check, ACTLOG Audit Attribution) |
| **5. Secure Integrations** | 4 | 4 | **0** | ✅ Fully Compliant (OAuth 2.1 / OIDC Bearer Auth, HTTP TLS, Keyring Secret Resolution) |
| **6. Non-Repudiation & Forensics** | 5 | 5 | **0** | ✅ Fully Compliant (User Identity Binding, Fail-Closed Audit, ISO 8601 UTC) |
| **Post-Implementation Residuals (RG)** | 7 | 7 | **0** | ✅ Fully Compliant (Production Guards, Silent Execution, Automated Tests) |
| **7. Dynamic Authentication (DAUTH)** | 11 | 11 | **0** | ✅ Fully Compliant (Challenge-Response, TTL, Privilege, Delegation, Credential Lifecycle, Target-Server Binding) |
| **Total** | **44** | **44** | **0** | **100% Resolved — 88/88 Tests Passing** |

---

## 3. Security Domains & Validated Controls

### 3.1 Domain 1: Network Security
- **Status**: 0 Open Gaps.
- **Implemented Controls**:
  - `_validate_session_security()` in [`mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py:72) enforces `SESSIONSECURITY=STRICT` across all configured accounts at startup.
  - Startup bypass flag (`SP_MCP_SKIP_SECURITY_CHECKS=1`) is strictly blocked in production environments (`SP_MCP_ENV=production` → `sys.exit(1)`).
  - SSH Ed25519 public key authentication with `StrictHostKeyChecking=yes` replaces legacy `sshpass`.
  - Client configuration template `config/dsm.sys.template` mandates `SSLREQUIRED Yes` and `SSL Yes`.

### 3.2 Domain 2: Identity & Credentials Management
- **Status**: 0 Open Gaps.
- **Implemented Controls**:
  - Five isolated privilege-tiered service accounts supported (`system`, `policy`, `storage`, `operator`, `readonly`) via [`config.ServerConfig`](../../src/sp_mcp_server/config.py:33).
  - Idempotent provisioning script ([`scripts/provision-sp-service-accounts.sh`](../../scripts/provision-sp-service-accounts.sh)) registers all five tiered accounts on the SP server with `SESSIONSECURITY=STRICT` and `MFAREQUIRED=NO` (CRED-5 / AUD-07).
  - Encrypted password stash mode (`SP_MCP_USE_PASSWORD_STASH=1`) eliminates plaintext `-PA=` arguments from process execution.
  - POSIX file permission verification (`secure_startup()`) strictly rejects world- or group-readable `.env` files across all 16 server entry points.
  - Keyring-first resolution (`_get_password()`) resolves service account passwords from OS keyring prior to environment variables.

### 3.3 Domain 3: Access Management
- **Status**: 0 Open Gaps.
- **Implemented Controls**:
  - Every tool command derives from `BaseCommand`, `BaseOfflineCommand`, or `BaseServermonCommand`, declaring an explicit `required_privilege`.
  - Self-narrowing tool registration (`_PRIVILEGE_SATISFIES`) dynamically queries the connected administrator's SP authority and registers only authorized tools.
  - Controlled offline privilege escalation uses `sudo -u <instance_user> -- <binary>` under `/etc/sudoers.d/sp-mcp-server` allowlists.

### 3.4 Domain 4: Policy Management
- **Status**: 0 Open Gaps.
- **Implemented Controls**:
  - Command approval lifecycle tools (`ApprovePendingCmd`, `RejectPendingCmd`, `WithdrawPendingCmd`) implement two-person integrity for destructive operations.
  - Password pre-validation (`_validate_password_policy`) queries `QUERY OPTION MINPWLENGTH` before issuing user or node registration commands.
  - Startup lockout check (`_check_lockout_policy`) verifies `INVALIDPWLIMIT > 0` on the Storage Protect server.
  - Audit trail correlation emits `DEFINE SCRATCHPADENTRY MCP_AUDIT` before write operations; failures trigger `SECURITY [POL-4 / RG-4]` error alerts.

### 3.5 Domain 5: Secure Integrations
- **Status**: 0 Open Gaps.
- **Implemented Controls**:
  - `OIDCBearerMiddleware` validates OAuth 2.1 / OIDC JWT tokens and maps token scopes (`mcp:*`) to SP privilege classes on HTTP transport.
  - Application-layer TLS verification enforces `SP_TLS_CERT` and `SP_TLS_KEY` presence before binding HTTP SSE endpoints.
  - Cloud storage connections (`commands/system/conn.py`) resolve access keys via secrets indirection (`keyring:`, `env:`), executing silently without exposing credentials in logs.

### 3.6 Domain 6: Non-Repudiation & Forensic Auditability
- **Status**: 0 Open Gaps.
- **Implemented Controls**:
  - `current_audit_user` ContextVar captures authenticated OIDC subject (`sub`) or `SP_MCP_USER` in [`mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py) and [`http_server.py`](../../src/sp_mcp_server/http_server.py) (**NR-1**).
  - Activity Log scratchpad entry embeds full identity: `DEFINE SCRATCHPADENTRY MCP_AUDIT DESCRIPTION="MCP_AUDIT user=<id> tool=<name> priv=<priv> corr=<uuid>"` (**NR-1**).
  - Strict audit fail-closed mode (`SP_MCP_STRICT_AUDIT=1`) aborts administrative write operations if ACTLOG audit recording fails (**NR-4**).
  - Standardized ISO 8601 UTC timestamp format (`%Y-%m-%dT%H:%M:%SZ`) configured across all logging handlers via `time.gmtime` (**NR-5**).
  - Storage Protect host hardening runbooks define tamper-resistant log attributes (`chattr +a`), restricted directories (`0700`), and 90-day retention (`SET SCRATCHPADRETENTION 90`, `SET ACTLOGRETENTION 90`) (**NR-2**, **NR-3**).

### 3.7 Domain 7: Dynamic & Delegated Authentication (DAUTH)
- **Status**: 0 Open Gaps.
- **Implemented Controls** (DAUTH-1 through DAUTH-9):
  - `SP_MCP_AUTH_MODE=dynamic` triggers a structured `AUTHENTICATION_REQUIRED` challenge for unauthenticated tool calls in [`mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py) (**DAUTH-1**).
  - `AuthenticateSession.execute()` in [`commands/system/auth.py`](../../src/sp_mcp_server/commands/system/auth.py) verifies credentials via zero-trace `execute_silent()`, parses SP authority, and mints a bounded `SessionLease` (**DAUTH-2**).
  - `SessionManager` enforces sliding inactivity TTL and absolute `MAX_SESSION_TTL_SECONDS`; all operations synchronized via `RLock` (**DAUTH-3**, **DAUTH-6**).
  - Session privilege is enforced at tool invocation; insufficient privilege yields `AUTHORIZATION_DENIED` before command execution (**DAUTH-4**).
  - Delegated session credentials (`username`, `password`) are applied through `current_execution_credentials` context variable; cleared in the `finally` block after each tool call (**DAUTH-5**, **DAUTH-5b**).
  - Dedicated subprocess assertions confirm that `-ID=` and `-PA=` arguments are passed when `current_execution_credentials` is set (**DAUTH-5a**).
  - `_check_session_target_server()` enforces `SessionLease.target_server` binding; sessions authenticated against one server stanza are rejected with `AUTHORIZATION_DENIED` if reused against a different one (**DAUTH-7**). Single-server deployments skip the check.
  - `SessionLease.password` is set to `None` on every removal path — `revoke_session()`, expiry in `get_session()`, bulk `cleanup_expired()`, and `clear()` at shutdown (**DAUTH-8** / AUD-08).
  - `LogoutSession` tool (`logout_session`, `required_privilege: any`) allows users to explicitly revoke their session, zeroing the in-memory credential and clearing audit context variables (**DAUTH-9** / AUD-08).

---

## 4. Residual & Non-Repudiation Gap Verification Summary

All 7 post-implementation residual gaps (RG-1 through RG-7) are closed and covered by automated regression tests in [`tests/test_security_controls.py`](../../tests/test_security_controls.py):

| Item | Control Focus | Source Implementation | Test Validation | Current Status |
| :--- | :--- | :--- | :--- | :---: |
| **RG-1** | Production startup guard | [`mcp_factory.py:93-109`](../../src/sp_mcp_server/mcp_factory.py) | `TestProductionGuard` | ✅ Validated |
| **RG-2** | Atomic `.env` permission check | [`config.py:117`](../../src/sp_mcp_server/config.py) | `TestEnvFilePermissions`, `TestSecureStartup` | ✅ Validated |
| **RG-3** | Silent execution for password tools | [`commands/base.py:92`](../../src/sp_mcp_server/commands/base.py) | `TestPasswordCommandsSilentExecution` | ✅ Validated |
| **RG-4** | SIEM-alertable audit write logging | [`mcp_factory.py:386-401`](../../src/sp_mcp_server/mcp_factory.py) | `TestAuditTrail` | ✅ Validated |
| **RG-5** | Application-layer HTTP TLS gate | [`main.py:115-146`](../../src/sp_mcp_server/main.py) | `TestHttpTransportTLS` | ✅ Validated |
| **RG-6** | Automated regression test coverage | [`tests/test_security_controls.py`](../../tests/test_security_controls.py) | 55 security unit tests (75 total across all test files) | ✅ Validated |
| **RG-7** | Node group member tools confirmation | [`commands/clients/groups.py`](../../src/sp_mcp_server/commands/clients/groups.py) | Source verified | ✅ Validated |
| **NR-1** | User identity binding in SP ACTLOG | [`mcp_factory.py:16,380`](../../src/sp_mcp_server/mcp_factory.py)<br>[`http_server.py:144`](../../src/sp_mcp_server/http_server.py) | `TestAuditTrail::test_scratchpad_entry_called_before_write` | ✅ Validated |
| **NR-2** | Local log tamper resistance | Host runbooks & SIEM forwarding | Deployment & OS permissions | 📋 Hardened |
| **NR-3** | Selective read auditability | Architecture design & `query_activity_log` | Validated in design | ✅ Validated |
| **NR-4** | Strict audit fail-closed enforcement | [`mcp_factory.py:403`](../../src/sp_mcp_server/mcp_factory.py) | `TestAuditTrail::test_strict_audit_fail_closed_aborts_execution` | ✅ Validated |
| **NR-5** | Standardized ISO 8601 UTC timestamps | [`mcp_factory.py:38`](../../src/sp_mcp_server/mcp_factory.py) | Formatter verified | ✅ Validated |
| **DAUTH-1..6** | Dynamic authentication (challenge, auth, TTL, privilege, delegation) | [`session.py`](../../src/sp_mcp_server/session.py) · [`auth.py`](../../src/sp_mcp_server/commands/system/auth.py) · [`mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py) | `TestDynamicAuthentication`, `TestDelegatedSubprocess`, `TestOIDCAuthorization` | ✅ Validated |
| **DAUTH-7** | `target_server` binding via `_check_session_target_server()` | [`mcp_factory.py`](../../src/sp_mcp_server/mcp_factory.py) | `TestTargetServerBinding` (6 paths) | ✅ Validated |
| **DAUTH-8** | `SessionLease.password` zeroed on all removal paths | [`session.py`](../../src/sp_mcp_server/session.py) | `TestSessionCredentialLifecycle` (4 paths) | ✅ Validated |
| **DAUTH-9** | `logout_session` explicit revocation tool | [`commands/system/auth.py`](../../src/sp_mcp_server/commands/system/auth.py) | `TestSessionCredentialLifecycle` (3 paths) | ✅ Validated |
| **CRED-5** | Tiered service account provisioning script | [`scripts/provision-sp-service-accounts.sh`](../../scripts/provision-sp-service-accounts.sh) | Script present; deployment execution | ✅ Validated |

---

## 5. Ongoing Operational Recommendations

To maintain the established security baseline, operators should:
1. Run `bash scripts/provision-sp-service-accounts.sh` once per IBM SP server to register tiered service accounts with `SESSIONSECURITY=STRICT` and `MFAREQUIRED=NO` (idempotent).
2. Configure `PASSWORDACCESS GENERATE` in `dsm.sys` (template: `config/dsm.sys.template`) and initialize credentials via interactive `dsmadmc` once per account.
3. Configure `SET COMMANDAPPROVAL ON` and `SET APPROVERSREQUIREAPPROVAL ON` on the Storage Protect server for destructive command protection.
4. Set server-wide account lockout thresholds (`SET INVALIDPWLIMIT 5`) and password minimum length (`SET MINPWLENGTH 15`).
5. Run automated test suites (`poetry run pytest tests/`) before and after any deployment updates.
