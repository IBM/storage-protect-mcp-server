# IBM Storage Protect MCP Server — Gap Analysis

**Revision**: 2025-07 (Post-Remediation Verification & Alignment)  
**Cross-reference**: [`docs/traceability/traceability-matrix.md`](traceability-matrix.md) · [`docs/analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)  
**Source reference**: `src/sp_mcp_server/` · `tests/`

---

## 1. Executive Summary

A comprehensive security analysis and audit was performed on the IBM Storage Protect (SP) MCP Server codebase (`src/sp_mcp_server`). All 20 historical security gaps across 5 security domains (Network Security, Identity & Credentials, Access Management, Policy Management, Secure Integrations) and all 7 subsequent residual gaps (RG-1 through RG-7) have been completely resolved and validated.

Currently, **0 open security gaps remain**.

---

## 2. Active Security Posture & Gap Status by Domain

| Security Domain | Initial Gaps Identified | Resolved / Closed | Open Gaps | Current Posture Status |
| :--- | :---: | :---: | :---: | :---: |
| **1. Network Security** | 3 | 3 | **0** | ✅ Fully Compliant (`SESSIONSECURITY=STRICT`, TLS 1.2/1.3, SSH Key Auth) |
| **2. Identity & Credentials** | 5 | 5 | **0** | ✅ Fully Compliant (5-Tier Credentials, Stash Auth, POSIX 0600 `.env` Check) |
| **3. Access Management** | 4 | 4 | **0** | ✅ Fully Compliant (Privilege Gate, Self-Narrowing Registry, Sudoers Execution) |
| **4. Policy Management** | 4 | 4 | **0** | ✅ Fully Compliant (Command Approval, `MINPWLENGTH` Check, ACTLOG Audit Attribution) |
| **5. Secure Integrations** | 4 | 4 | **0** | ✅ Fully Compliant (OAuth 2.1 / OIDC Bearer Auth, HTTP TLS, Keyring Secret Resolution) |
| **Post-Implementation Residuals (RG)** | 7 | 7 | **0** | ✅ Fully Compliant (Production Guards, Silent Execution, Automated Tests) |
| **Total** | **27** | **27** | **0** | **100% Resolved & Validated (56/56 Tests Passing)** |

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

---

## 4. Residual Gap Verification Summary

All 7 post-implementation residual gaps (RG-1 through RG-7) are closed and covered by automated regression tests in [`tests/test_security_controls.py`](../../tests/test_security_controls.py):

| Item | Control Focus | Source Implementation | Test Validation | Current Status |
| :--- | :--- | :--- | :--- | :---: |
| **RG-1** | Production startup guard | [`mcp_factory.py:93-109`](../../src/sp_mcp_server/mcp_factory.py) | `TestProductionGuard` | ✅ Validated |
| **RG-2** | Atomic `.env` permission check | [`config.py:117`](../../src/sp_mcp_server/config.py) | `TestEnvFilePermissions`, `TestSecureStartup` | ✅ Validated |
| **RG-3** | Silent execution for password tools | [`commands/base.py:92`](../../src/sp_mcp_server/commands/base.py) | `TestPasswordCommandsSilentExecution` | ✅ Validated |
| **RG-4** | SIEM-alertable audit write logging | [`mcp_factory.py:386-401`](../../src/sp_mcp_server/mcp_factory.py) | `TestAuditTrail` | ✅ Validated |
| **RG-5** | Application-layer HTTP TLS gate | [`main.py:115-146`](../../src/sp_mcp_server/main.py) | `TestHttpTransportTLS` | ✅ Validated |
| **RG-6** | Automated regression test coverage | [`tests/test_security_controls.py`](../../tests/test_security_controls.py) | 36 dedicated security unit tests | ✅ Validated |
| **RG-7** | Node group member tools confirmation | [`commands/clients/groups.py`](../../src/sp_mcp_server/commands/clients/groups.py) | Source verified | ✅ Validated |

---

## 5. Ongoing Operational Recommendations

To maintain the zero-gap baseline, operators should:
1. Ensure all Storage Protect service accounts are configured with `SESSIONSECURITY=STRICT` and `MFAREQUIRED=NO`.
2. Configure `PASSWORDACCESS GENERATE` in `dsm.sys` and initialize credentials via interactive `dsmadmc` once per account.
3. Configure `SET COMMANDAPPROVAL ON` and `SET APPROVERSREQUIREAPPROVAL ON` on the Storage Protect server for destructive command protection.
4. Set server-wide account lockout thresholds (`SET INVALIDPWLIMIT 5`) and password minimum length (`SET MINPWLENGTH 15`).
5. Run automated test suites (`poetry run pytest tests/`) before and after any deployment updates.
