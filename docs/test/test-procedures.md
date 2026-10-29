# Test Execution Procedures & Runbooks

* **Document**: Test Procedures for IBM Storage Protect MCP Server
* **Revision**: 2026-10
* **Status**: Complete & Verified
* **Target Audience**: Quality Engineers, Security Auditors, CI/CD Maintainers, and Storage Administrators
* **Inputs**: [`test-specifications.md`](test-specifications.md), [`test-cases.md`](test-cases.md), [`docs/guides/`](../guides/), and `tests/`

---

## Runbook Index

| Procedure ID | Procedure Title | Scope | Execution Frequency |
| :--- | :--- | :--- | :--- |
| **PROC-01** | [Automated Unit & Mock Regression Suite](#proc-01-automated-unit--mock-regression-suite) | All 12 test files (188 tests) | Pre-commit, PR CI build |
| **PROC-02** | [Security Controls Verification Runbook](#proc-02-security-controls-verification-runbook) | NET, CRED, ACC, POL, NR, RG security tests | Nightly, Security audit |
| **PROC-03** | [Dynamic Authentication & Session Lifecycle Runbook](#proc-03-dynamic-authentication--session-lifecycle-runbook) | Challenge-response, TTL, Zeroing | Release verification |
| **PROC-04** | [OAuth 2 & HTTP Transport Verification Runbook](#proc-04-oauth-2--http-transport-verification-runbook) | AS metadata, JWKS, Introspection, RFC 9470 | Release verification |
| **PROC-05** | [Persona Prompt & AI Workflow Validation Runbook](#proc-05-persona-prompt--ai-workflow-validation-runbook) | Personas R-01 through R-08 (88 tests) | Sprint validation |
| **PROC-06** | [Live IBM Storage Protect Integration Procedure](#proc-06-live-ibm-storage-protect-integration-procedure) | End-to-end integration with live SP staging | Staging deployment |
| **PROC-07** | [Cross-Platform Portability (Windows / Linux) Procedure](#proc-07-cross-platform-portability-procedure) | Platform guards & permissions | Platform qualification |
| **PROC-08** | [Troubleshooting & Diagnostic Runbook](#proc-08-troubleshooting--diagnostic-runbook) | Test failure diagnosis & state cleanup | On-demand debugging |

---

## PROC-01: Automated Unit & Mock Regression Suite

### 1.1 Objective
Execute the complete automated test suite locally or in CI pipelines to verify that all unit, mock CLI, security regression, and prompt template tests pass with zero failures.

### 1.2 Prerequisites
1. Python 3.10+ installed (`python --version`).
2. Virtual environment initialized and activated.
3. Package installed in editable mode:
   ```bash
   pip install -e ".[test,sse]"
   # Or using requirements files:
   pip install -r requirements.txt -r requirements-test.txt -r requirements-sse.txt
   ```
4. Dependency integrity verified:
   ```bash
   python -m pip check
   # Expected output: "No broken requirements found."
   ```

### 1.3 Execution Steps
Run the full test suite from the repository root:

```bash
# Standard verbose execution
python -m pytest -v

# Short progress execution
python -m pytest -q
```

### 1.4 Expected Results
```
====================== 170 passed, 18 skipped in 10.97s =======================
```
* **Passed**: Exactly **170 unit/mock tests**.
* **Skipped**:
  * 15 live integration tests in `tests/test_sample_prompts_positive.py` (skipped when no live SP server is connected).
  * 3 POSIX permission tests in `tests/test_sec_startup.py` when executing on Windows (due to NTFS permission semantics).
* **Failures / Errors**: **0**.

---

## PROC-02: Security Controls Verification Runbook

### 2.1 Objective
Independently validate the security controls across Network Security (NET), Identity & Credentials (CRED), Access Management (ACC), Policy Management (POL), Non-Repudiation (NR), and Residual Invariant Guards (RG).

### 2.2 Execution Steps
Run the targeted security test files:

```bash
# 1. Startup & privilege filtering controls (NET-1, RG-1, CRED-3, RG-2, ACC-2, POL-3)
python -m pytest tests/test_sec_startup.py -v

# 2. Silent execution & credential masking (RG-3, CRED-2)
python -m pytest tests/test_sec_password_commands.py -v

# 3. ACTLOG scratchpad attribution & HTTP TLS enforcement (POL-4, RG-4, NR-1, NR-4, RG-5)
python -m pytest tests/test_sec_audit_trail.py -v
```

### 2.3 Verification Criteria
1. **Startup Fail-Closed**: Verify that simulating a non-STRICT session security (`SESSIONSECURITY=Transitional`) halts startup with exit code 1.
2. **Production Guard**: Verify that setting `SP_MCP_ENV=production` and `SP_MCP_SKIP_SECURITY_CHECKS=1` terminates immediately.
3. **Log Sanitization**: Inspect `tests/test_sec_password_commands.py` assertions to ensure plaintext passwords never appear in captured logs (`caplog`).
4. **Strict Audit Abort**: Verify that simulating a scratchpad failure with `SP_MCP_STRICT_AUDIT=1` prevents tool execution and returns a descriptive error.

---

## PROC-03: Dynamic Authentication & Session Lifecycle Runbook

### 3.1 Objective
Verify Model B dynamic challenge-response authentication, bounded session TTLs, delegated CLI execution, memory zeroing on deletion, and cross-server binding.

### 3.2 Execution Steps
```bash
# Run dynamic auth tests
python -m pytest tests/test_sec_dynamic_auth.py -v

# Run session lifecycle & server binding tests
python -m pytest tests/test_sec_session_lifecycle.py -v
```

### 3.3 Verification Checkpoints
- **Challenge-Response**: Unauthenticated tool calls must return JSON structure containing:
  ```json
  {
    "is_error": true,
    "error_type": "AUTHENTICATION_REQUIRED",
    "message": "Dynamic authentication required for this session.",
    "supported_auth_tools": ["authenticate_session"],
    "required_parameters": ["admin_id", "password"]
  }
  ```
- **Target Server Protection**: Verify that a session issued for server `spsvr01.corp` is rejected with `AUTHORIZATION_DENIED` when attempted against `spsvr02.corp`.
- **Memory Zeroing**: Verify that `session.password` is overwritten upon `logout_session`, `revoke_session()`, and background expiration.

---

## PROC-04: OAuth 2 & HTTP Transport Verification Runbook

### 4.1 Objective
Validate the OAuth 2.1 / OIDC extended middleware (OA-1 through OA-7) and HTTP transport TLS enforcement.

### 4.2 Automated Test Execution
```bash
python -m pytest tests/test_sec_oauth2.py -v
```
All 26 automated tests across the 6 test classes must pass.

### 4.3 Integration Testing with Local Keycloak IdP
To validate against a running Keycloak identity provider, follow [`docs/guides/local-idp-oauth2-guide.md`](../guides/local-idp-oauth2-guide.md):

1. **Start Local Keycloak**:
   ```bash
   docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin -e KEYCLOAK_ADMIN_PASSWORD=admin \
     quay.io/keycloak/keycloak:24.0.0 start-dev
   ```
2. **Configure `.env`**:
   ```dotenv
   SP_OIDC_ISSUER=http://localhost:8080/realms/mcp-demo
   SP_OIDC_AUDIENCE=sp-mcp-server
   SP_TLS_CERT=/opt/sp-mcp-server/certs/server.crt
   SP_TLS_KEY=/opt/sp-mcp-server/certs/server.key
   SP_MCP_PUBLIC_URL=https://localhost:8443
   ```
3. **Start HTTP Server**:
   ```bash
   python -m sp_mcp_server.main --transport http --port 8443
   ```
4. **Test RFC 8414 Endpoint**:
   ```bash
   curl -k https://localhost:8443/.well-known/oauth-authorization-server
   ```
5. **Test RFC 9470 Endpoint**:
   ```bash
   curl -k https://localhost:8443/.well-known/oauth-protected-resource
   ```

---

## PROC-05: Persona Prompt & AI Workflow Validation Runbook

### 5.1 Objective
Validate AI client interactions, prompt template evaluations, and multi-step tool calls across all eight operational personas defined in [`docs/example/sample-prompts.md`](../example/sample-prompts.md) (88 tests total).

### 5.2 Execution Steps
```bash
# Execute entire persona prompt test suite
pytest tests/test_sample_prompts_positive.py -v

# Run targeted persona prompt suites
pytest tests/test_sample_prompts_positive.py -k "TestR01" -v  # Operator
pytest tests/test_sample_prompts_positive.py -k "TestR02" -v  # Administrator
pytest tests/test_sample_prompts_positive.py -k "TestR03" -v  # Solution Architect
pytest tests/test_sample_prompts_positive.py -k "TestR04" -v  # Workload Owner
pytest tests/test_sample_prompts_positive.py -k "TestR05" -v  # Security Officer
pytest tests/test_sample_prompts_positive.py -k "TestR06" -v  # Resilience Operations
pytest tests/test_sample_prompts_positive.py -k "TestR07" -v  # Service Engineer
pytest tests/test_sample_prompts_positive.py -k "TestR08" -v  # Multi-Server Replication
pytest tests/test_sample_prompts_positive.py -k "TestPromptToolPrivilegeAnnotations" -v  # Access Tier Guards
```

### 5.3 Test Suite Coverage
- **R-01 (Data Protection Operator)** (21 Tests): Discovery (`QUERY STATUS`, `QUERY SESSION`), backup policy, scheduling associations, storage pool configuration, and node lifecycle.
- **R-02 (Data Protection Administrator)** (6 Tests): Performance tuning (`TXNGROUPMAX`, `MOVEBATCHSIZE`), recovery log diagnostics (`QUERY LOG`), and operational audits.
- **R-03 (Infrastructure Solution Architect)** (4 Tests): Container deduplication analysis (`QUERY DEDUPSTATS`), device class inspections (`QUERY DEVCLASS`), storage pool directory expansions, and license compliance audits.
- **R-04 (Workload & Application Owner)** (3 Tests): Application backup volume validation (`QUERY FILESPACE`), SAP redo-log archiving copy group definitions (`DEFINE COPYGROUP`), and Oracle occupancy analysis (`QUERY OCCUPANCY`).
- **R-05 (Security & Compliance Officer)** (10 Tests): Dual-custody command approvals (`APPROVE PENDINGCMD`), session security audits (`SESSIONSECURITY=STRICT`), lockout enforcement, and policy set retention rules.
- **R-06 (Resilience Operations Manager)** (4 Tests): Suspected ransomware node isolation (`SetClientLock`), database disaster recovery restore invocation (`RestoreDB`), DR plan file status queries (`QueryRecoveryPlanFile`), and offsite media tracking (`QueryDRMedia`).
- **R-07 (Storage Protect Service Engineer)** (3 Tests): Servermon diagnostic utility execution (`RunServerMon`), activity log defect triage (`ANR0406E`), and cloud migration warning frequency analysis (`ANR8468W`).
- **R-08 (Multi-Server Replication & Data Management)** (7 Tests): Multi-server replication topology discovery (`QueryReplicationServer`), replication rules (`QueryReplicationRule`), failure record retrieval (`QueryReplicationFailures`), per-node replication progress (`QueryReplicationStatus`), storage pool synchronization (`QueryProtectionStatus`), failover node updating (`UpdateNode`), and storage rules (`QueryStorageRule`).
- **Tool Privilege Tier Annotations** (30 Tests): Parameterized checks verifying that all tools invoked in sample prompts enforce exact privilege levels and read-only invariants.

---

## PROC-06: Live IBM Storage Protect Integration Procedure

### 6.1 Objective
Execute the 15 live integration tests in `tests/test_sample_prompts_positive.py` against a real IBM Storage Protect staging server.

### 6.2 Prerequisites
1. Dedicated non-production IBM Storage Protect staging server (v8.1.18+).
2. Service accounts provisioned using [`scripts/provision-sp-service-accounts.sh`](../../scripts/provision-sp-service-accounts.sh):
   ```bash
   bash scripts/provision-sp-service-accounts.sh -s spsvr01.corp -a admin -p <admin_pwd>
   ```
3. Staging `.env` configured:
   ```dotenv
   TCPSERVERADDRESS=spsvr01.corp.example.com
   SP_SERVER_PORT=1500
   SP_ADMIN_ID_SYSTEM=mcp-svc-system
   SP_ADMIN_PASSWORD_SYSTEM=<password>
   SP_ADMIN_ID_POLICY=mcp-svc-policy
   SP_ADMIN_PASSWORD_POLICY=<password>
   SP_ADMIN_ID_STORAGE=mcp-svc-storage
   SP_ADMIN_PASSWORD_STORAGE=<password>
   SP_ADMIN_ID_OPERATOR=mcp-svc-operator
   SP_ADMIN_PASSWORD_OPERATOR=<password>
   SP_ADMIN_ID_READONLY=mcp-svc-readonly
   SP_ADMIN_PASSWORD_READONLY=<password>
   SP_MCP_RUN_LIVE_TESTS=1
   ```

### 6.3 Execution
```bash
python -m pytest tests/test_sample_prompts_positive.py -v
```

### 6.4 Post-Test Audit Inspection
Log into the IBM Storage Protect server via `dsmadmc` and inspect the Activity Log:
```
dsmadmc -id=admin -pa=<password> "QUERY ACTLOG SEARCH=MCP_AUDIT"
```
Verify that scratchpad records were emitted with correct correlation keys:
```
ANR9999D MCP_AUDIT user=mcp-svc-system authmodel=local tool=... priv=system corr=...
```

---

## PROC-07: Cross-Platform Portability Procedure

### 7.1 Linux Production Validation
- **Permissions Verification**:
  ```bash
  chmod 600 .env
  ls -la .env # Verify: -rw-------
  pytest tests/test_sec_startup.py -k "TestEnvFilePermissions"
  ```
- **Sudoers Non-Root Verification**:
  ```bash
  sudo -u mcp-runner python3 -m sp_mcp_server.main --mode read_only
  ```

### 7.2 Windows Development Validation
- In Windows PowerShell, verify execution under `.venv`:
  ```powershell
  .\.venv\Scripts\python -m pytest
  ```
- Verify that POSIX chmod bit checks are cleanly skipped without `SystemExit(1)`.

---

## PROC-08: Troubleshooting & Diagnostic Runbook

### 8.1 Symptom: ContextVar State Pollution (Ordering Failure)
* **Symptom**: 3 tests fail in `TestDynamicAuthentication` when running the entire suite.
* **Diagnosis**: ContextVars or globals (`_process_session_id`, `_process_audit_user`) were left in a non-default state by preceding tests.
* **Resolution**:
  - Ensure [`tests/conftest.py`](../../tests/conftest.py) exists and contains the `clean_test_execution_state` autouse fixture.
  - Verify that `reset_execution_state()` is invoked before each test.

### 8.2 Symptom: `ResolutionImpossible` on Package Installation
* **Symptom**: `pip install` fails with conflicting version errors.
* **Diagnosis**: `pyproject.toml` and `requirements.txt` require conflicting `mcp` versions.
* **Resolution**: Verify that both `pyproject.toml` and `requirements.txt` specify `mcp>=2.3.0,<2.4.0`.

### 8.3 Symptom: `SystemExit: 1` during Startup on Windows
* **Symptom**: `TestEnvFilePermissions` fails immediately when running on Windows.
* **Diagnosis**: NTFS does not support POSIX `0600` permission masks.
* **Resolution**: Verify that `_load_env_permission_check()` in `src/sp_mcp_server/config.py` contains `if os.name == 'nt': return`.

---

## PROC-09: Controlled Fault Injection & Resilience Testing Runbook

### 9.1 Objective
Verify server resilience, timeout handling, subprocess failure containment, and network partition recovery using the containerized test-bed defined in [`docs/test/test-bed.md`](test-bed.md).

### 9.2 Test-Bed Environment Bring-Up
1. Launch the test-bed container stack:
   ```bash
   docker compose -f docker-compose.testbed.yml up -d
   ```
2. Verify all 5 containers are running healthy:
   ```bash
   docker compose -f docker-compose.testbed.yml ps
   # Expected: sp-server-mock, toxiproxy, mock-idp, sp-mcp-under-test, locust-load-injector
   ```

### 9.3 Subprocess CLI Fault Injection via `fault_dsmadmc.py`
The CLI shim reads `/tmp/sp_fault_injection.json` to dynamically inject failures without modifying server code.

1. **Inject Subprocess Connection Failure (`ANS1017E`)**:
   ```bash
   docker exec sp-mcp-under-test bash -c 'cat << "EOF" > /tmp/sp_fault_injection.json
   {
     "rules": [
       {
         "match_cmd": "QUERY STATUS",
         "exit_code": 8,
         "stderr": "ANS1017E (RC-50) Server connection failed: TCP/IP connection failure.",
         "stdout": ""
       }
     ]
   }
   EOF'
   ```
   Execute test query and assert graceful error handling:
   ```bash
   docker exec sp-mcp-under-test python -m pytest tests/test_resilience_faults.py -k "test_connection_failure_ans1017e"
   ```

2. **Inject CLI Subprocess Infinite Hang (Watchdog Timeout)**:
   ```bash
   docker exec sp-mcp-under-test bash -c 'cat << "EOF" > /tmp/sp_fault_injection.json
   {
     "rules": [
       {
         "match_cmd": "QUERY",
         "delay_seconds": 60.0
       }
     ]
   }
   EOF'
   ```
   Execute watchdog test (verifying process terminated after 30s timeout):
   ```bash
   docker exec sp-mcp-under-test python -m pytest tests/test_resilience_faults.py -k "test_subprocess_timeout_watchdog"
   ```

3. **Clear Subprocess Faults**:
   ```bash
   docker exec sp-mcp-under-test rm -f /tmp/sp_fault_injection.json
   ```

### 9.4 Network Chaos Injection via Toxiproxy
1. **Inject 5000ms Latency on SP Storage Protect Port**:
   ```bash
   curl -X POST http://localhost:8474/proxies/sp-backend/toxics \
     -H "Content-Type: application/json" \
     -d '{"name": "latency_spike", "type": "latency", "attributes": {"latency": 5000, "jitter": 500}}'
   ```
   Execute test suite to verify operation completes within extended timeout:
   ```bash
   docker exec sp-mcp-under-test python -m pytest tests/test_resilience_faults.py -k "test_network_latency_resilience"
   ```

2. **Inject TCP Connection Reset During Streaming**:
   ```bash
   curl -X POST http://localhost:8474/proxies/client-sse/toxics \
     -H "Content-Type: application/json" \
     -d '{"name": "peer_reset", "type": "reset_peer", "attributes": {"timeout": 2000}}'
   ```
   Verify server terminates SSE generator cleanly without leaking socket descriptors:
   ```bash
   docker exec sp-mcp-under-test python -m pytest tests/test_resilience_faults.py -k "test_sse_client_reset_cleanup"
   ```

3. **Reset Toxiproxy**:
   ```bash
   curl -X POST http://localhost:8474/reset
   ```

---

## PROC-10: Stress, Concurrency & Capacity Testing Runbook

### 10.1 Objective
Validate server throughput, connection scaling (100–200 concurrent sessions), rate-limiting throttling, memory RSS stability (<= 256MB), and zero descriptor leakage under continuous synthetic load.

### 10.2 Headless Locust Load Simulation
1. Launch headless Locust benchmark against the running test-bed server:
   ```bash
   docker exec locust-load-injector locust \
     -f /tests/load/locustfile.py \
     --headless \
     -u 100 \
     -r 10 \
     --run-time 10m \
     --host http://sp-mcp-under-test:8000 \
     --csv /artifacts/stress_results
   ```

2. **Monitor Server Process Health in Real-Time**:
   ```bash
   docker exec sp-mcp-under-test python -c '
   import psutil, time, os
   p = psutil.Process()
   for _ in range(60):
       mem_mb = p.memory_info().rss / 1024 / 1024
       fds = p.num_fds() if hasattr(p, "num_fds") else len(p.open_files())
       print(f"Memory RSS: {mem_mb:.2f} MB | Open FDs: {fds}")
       time.sleep(10)
   '
   ```

### 10.3 High-Volume Ephemeral Dynamic Auth Churn (10,000 Sessions)
Execute the rapid session lifecycle stress script:
```bash
docker exec sp-mcp-under-test python -m pytest tests/load/test_session_churn.py -v
```

### 10.4 Quality Gate Threshold Verification (QG-9)
Evaluate results against [`test-specifications.md`](test-specifications.md) Gate QG-9:
- Total Requests: > 20,000
- Failure Rate: 0.00%
- p95 Latency: <= 500ms (excluding simulated backend latency)
- Peak Memory RSS: <= 256MB
- Leaked Sockets / File Descriptors: 0

---

## PROC-11: User Security Penetration & Adversarial Attack Simulation Runbook

### 11.1 Objective
Execute automated adversarial penetration test suites validating token tampering rejection, privilege boundary enforcement, command injection escaping, and ACTLOG non-repudiation attribution.

### 11.2 Automated Negative Security Suite Execution
```bash
pytest tests/test_sec_negative.py -v
```

### 11.3 Step-by-Step Adversarial Simulation Vectors

1. **Adversarial Token Forgery Attack**:
   Mint a rogue JWT signed with an untrusted ephemeral RSA key:
   ```python
   # tests/scripts/mint_rogue_jwt.py
   import jwt, time
   from cryptography.hazmat.primitives.asymmetric import rsa
   rogue_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
   token = jwt.encode(
       {"sub": "attacker@evil.com", "iss": "https://evil-idp.com", "exp": time.time() + 3600, "scope": "sp:admin"},
       rogue_key,
       algorithm="RS256",
       headers={"kid": "rogue-key-1"}
   )
   ```
   Send request to server:
   ```bash
   curl -k -i -X POST https://localhost:8000/sse \
     -H "Authorization: Bearer $token" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query_status", "arguments": {}}, "id": 1}'
   ```
   **Verify Expected Output**:
   ```http
   HTTP/1.1 401 Unauthorized
   WWW-Authenticate: Bearer error="invalid_token", error_description="Signature verification failed"
   ```

2. **Privilege Boundary Escalation Attack**:
   Send request with valid Operator-level token attempting to invoke `halt_server`:
   ```bash
   curl -k -i -X POST https://localhost:8000/sse \
     -H "Authorization: Bearer $operator_token" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "halt_server", "arguments": {}}, "id": 2}'
   ```
   **Verify Expected Output**:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 2,
     "error": {
       "code": -32001,
       "message": "AUTHORIZATION_DENIED: User 'operator' lacks required privilege tier 'system'."
     }
   }
   ```

3. **Dual-Custody Self-Approval Bypass Attempt**:
   Attempt to approve own pending command:
   ```bash
   curl -k -i -X POST https://localhost:8000/sse \
     -H "Authorization: Bearer $admin_token" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "approve_pending_command", "arguments": {"command_id": "PENDINGCMD_104"}}, "id": 3}'
   ```
   **Verify Expected Output**:
   ```json
   {
     "jsonrpc": "2.0",
     "id": 3,
     "error": {
       "code": -32002,
       "message": "DUAL_CUSTODY_VIOLATION: Command initiator cannot approve their own command."
     }
   }
   ```

4. **Shell Injection Escaping Validation**:
   Submit payload containing command separators:
   ```bash
   curl -k -i -X POST https://localhost:8000/sse \
     -H "Authorization: Bearer $admin_token" \
     -H "Content-Type: application/json" \
     -d '{"jsonrpc": "2.0", "method": "tools/call", "params": {"name": "query_node", "arguments": {"node_name": "NODE01; rm -rf /"}}, "id": 4}'
   ```
   **Verify Expected Output**:
   - Subprocess executed with argv `["dsmadmc", ..., "QUERY NODE \"NODE01; rm -rf /\""]`.
   - SP backend returns `ANR2034E No match found using this criteria`.
   - Zero shell command execution.

