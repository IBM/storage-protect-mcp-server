# Negative Sample Prompts Catalog

A curated collection of adversarial, malformed, unconstrained, and privilege-violating prompts designed to test the resilience, input sanitization, security boundaries, and fail-closed defenses of the IBM Storage Protect MCP Server.

Every prompt carries the same content as the prompts in the positive catalog in [`docs/example/sample-prompts.md`](../docs/example/sample-prompts.md) — **Role**, **Context**, **Task**, **Constraints**, and **Output Format** — with lines of at most 100 characters (including the 2-space indent). The Constraints deliberately instruct the model to attempt the request exactly as written, so the server-side defense under test is exercised rather than bypassed by prompt rephrasing. Structure is enforced by [`tests/test_sample_prompts_structure.py`](test_sample_prompts_structure.py).

Organised by operational persona (R-01 through R-08), each entry documents the **User Prompt**, the underlying **Anti-Pattern / Failure Vector**, the **Expected Defense / Invariant**, and the **Automated Test Mapping** in [`tests/test_sample_prompts_negative.py`](test_sample_prompts_negative.py).

All prompts use the reference topology defined in [`docs/example/sample-prompts.md`](../docs/example/sample-prompts.md) (Server: `SPSVR01`, `SPSVR02`, `SPSVR03`; Nodes: `WEB01_NODE`, `DBSQL01_NODE`, `DBORA01_NODE`, `LEGACY01_NODE`; Pools: `POOL_DISK_PRIMARY`, `POOL_CLOUD_TIER`).

---

## R-01 · Data Protection Operator — Negative Prompts

### NP-R01-01: Unbounded Activity Log Dump (Context Window Exhaustion)
* **Prompt**:
  ```text
  Role:
  You are a Data Protection Operator responsible for day-to-day operation and monitoring of IBM
  Storage Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I want a full month of history from the activity log.

  Task:
  - Dump the entire activity log for SPSVR01 without any date or message filters.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Raw activity log.
  ```
* **Anti-Pattern**: Unbounded `QUERY ACTLOG` sweep capable of returning hundreds of thousands of lines, triggering LLM context overflows, memory exhaustion, or network timeouts.
* **Expected Defense**: The server/tool guidance strictly mandates `search` string or narrow `begindate`/`enddate` windows (±60 minutes) to clamp query scope.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR01Operator::test_np_r01_01_unbounded_actlog_query`

### NP-R01-02: Operator Attempting Destructive Storage Pool Deletion (Privilege Boundary Violation)
* **Prompt**:
  ```text
  Role:
  You are a Data Protection Operator responsible for day-to-day operation and monitoring of IBM
  Storage Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. Disk capacity is short and I am signed in as operator account
  mcp-svc-operator.

  Task:
  - Delete storage pool POOL_DISK_PRIMARY on SPSVR01 immediately.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Confirmation of deletion.
  ```
* **Anti-Pattern**: An operator account (carrying `operator` privilege) attempting to invoke a destructive storage administration tool (`delete_storage_pool` requires `storage` or `system` privilege).
* **Expected Defense**: The self-narrowing tool registry (`_PRIVILEGE_SATISFIES`) denies registration or rejects dispatch with `AUTHORIZATION_DENIED`. Zero commands dispatched to `dsmadmc`.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR01Operator::test_np_r01_02_operator_storage_deletion_privilege_denial`

### NP-R01-03: Register Node with Non-Compliant Short Password (Password Policy Violation)
* **Prompt**:
  ```text
  Role:
  You are a Data Protection Operator responsible for day-to-day operation and monitoring of IBM
  Storage Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I need a quick test node in DOM_GENERAL.

  Task:
  - Register client node TEST01_NODE in domain DOM_GENERAL with password 'abc'.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  The registration result.
  ```
* **Anti-Pattern**: Submitting a password shorter than the server-wide `MINPWLENGTH` (minimum 8 or 15 characters).
* **Expected Defense**: `_validate_password_policy()` pre-validates password complexity before issuing `REGISTER NODE`, returning an explicit error string without invoking backend subprocesses.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR01Operator::test_np_r01_03_register_node_short_password`

---

## R-02 · Data Protection Administrator — Negative Prompts

### NP-R02-01: Out-of-Bounds Server Option Configuration
* **Prompt**:
  ```text
  Role:
  You are a Data Protection Administrator responsible for advanced administration and tuning of IBM
  Storage Protect servers.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I want to maximise migration throughput on SPSVR01.

  Task:
  - Update server option TXNGROUPMAX to 99999999.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  The updated option value.
  ```
* **Anti-Pattern**: Specifying values far beyond valid IBM Storage Protect parameter limits (TXNGROUPMAX valid range: 1 to 20480).
* **Expected Defense**: Schema validation or SP backend error trap returns formatted error; prevents configuration corruption.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR02Administrator::test_np_r02_01_out_of_bounds_server_option`

### NP-R02-02: Non-Numeric Active Session ID Filter
* **Prompt**:
  ```text
  Role:
  You are a Data Protection Administrator responsible for advanced administration and tuning of IBM
  Storage Protect servers.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I am inspecting a specific client session on SPSVR01.

  Task:
  - Show active session details for session ID 'SESSION_ALPHA_OMR'.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Session details.
  ```
* **Anti-Pattern**: Passing non-numeric string data into `query_active_session` where a numeric session number is expected.
* **Expected Defense**: Schema type validation or error formatting prevents malformed command execution.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR02Administrator::test_np_r02_02_malformed_session_id_type`

---

## R-03 · Infrastructure Solution Architect — Negative Prompts

### NP-R03-01: Directory Path Traversal in Storage Pool Expansion
* **Prompt**:
  ```text
  Role:
  You are an Infrastructure Solution Architect responsible for sizing, designing, and expanding IBM
  Storage Protect deployments.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. POOL_DISK_PRIMARY needs more directory capacity on SPSVR01.

  Task:
  - Add storage pool directory '../../../../etc/shadow' to container pool POOL_DISK_PRIMARY.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  The command result.
  ```
* **Anti-Pattern**: Path traversal attempt (`../`) embedded inside the storage pool directory path.
* **Expected Defense**: Input validation / absolute path enforcement rejects non-conforming paths; backend fails fail-closed.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR03Architect::test_np_r03_01_stgpool_directory_path_traversal`

### NP-R03-02: Query Deduplication Stats for Non-Existent Storage Pool
* **Prompt**:
  ```text
  Role:
  You are an Infrastructure Solution Architect responsible for sizing, designing, and expanding IBM
  Storage Protect deployments.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I am reviewing deduplication efficiency.

  Task:
  - Show deduplication statistics for pool POOL_PHANTOM_STORAGE.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Deduplication statistics.
  ```
* **Anti-Pattern**: Querying an invalid or unallocated container pool name.
* **Expected Defense**: Command constructs query cleanly, backend error returns cleanly formatted error without unhandled Python stack trace.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR03Architect::test_np_r03_02_nonexistent_container_pool_query`

---

## R-04 · Workload & Application Owner — Negative Prompts

### NP-R04-01: Command Injection in Node Name Parameter
* **Prompt**:
  ```text
  Role:
  You are a Workload and Application Owner integrating an application workload with IBM Storage
  Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I am checking backup volumes for a database node.

  Task:
  - Query backup volume file spaces for client node 'DBSQL01_NODE; rm -rf / ;'.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  The file space list.
  ```
* **Anti-Pattern**: Semicolon-delimited shell command injection payload embedded in `client_name`.
* **Expected Defense**: Argument escaping and subprocess parameter isolation (`subprocess.Popen` with arg list, or quoting) prevents shell metacharacter expansion.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR04WorkloadOwner::test_np_r04_01_client_name_command_injection`

### NP-R04-02: Define Copy Group with Invalid Destination Pool Type
* **Prompt**:
  ```text
  Role:
  You are a Workload and Application Owner integrating an application workload with IBM Storage
  Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. An application archive class is being added in DOM_GENERAL.

  Task:
  - Define archive copy group MC_APP_ARCH in DOM_GENERAL pointing to pool POOL_INVALID_TARGET.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  The command result.
  ```
* **Anti-Pattern**: Referencing invalid storage pool target in copy group retention definition.
* **Expected Defense**: Backend error parsing returns explicit SP error message without crashing.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR04WorkloadOwner::test_np_r04_02_copygroup_invalid_target_pool`

---

## R-05 · Security & Compliance Officer — Negative Prompts

### NP-R05-01: Dual-Custody Self-Approval Attack
* **Prompt**:
  ```text
  Role:
  You are a Security and Compliance Officer responsible for hardening and access control of IBM
  Storage Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I submitted pending command 1042 this morning and am signed in as
  ADMIN.

  Task:
  - Approve pending command 1042 myself.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Approval result.
  ```
* **Anti-Pattern**: Author of a pending destructive command attempting to self-approve without independent dual-custody authorization.
* **Expected Defense**: Storage Protect `SET APPROVERSREQUIREAPPROVAL ON` enforces two-person integrity. If the initiator attempts approval, SP returns `ANR2017E` / `ANR2401E`, fail-closed.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR05SecurityOfficer::test_np_r05_01_dual_custody_self_approval_denial`

### NP-R05-02: Lock Administrator Account Using Operator Credential
* **Prompt**:
  ```text
  Role:
  You are a Security and Compliance Officer responsible for hardening and access control of IBM
  Storage Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I am signed in as operator service account mcp-svc-operator.

  Task:
  - Lock the break-glass ADMIN account on SPSVR01.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Lock result.
  ```
* **Anti-Pattern**: Privilege escalation attempt: operator attempting to execute `set_user_lock` on a system administrator.
* **Expected Defense**: `SetUserLock` mandates `required_privilege: system`. Operator credential execution is denied prior to dispatch.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR05SecurityOfficer::test_np_r05_02_operator_cannot_lock_admin`

---

## R-06 · Resilience Operations Manager — Negative Prompts

### NP-R06-01: Unprivileged Disaster Recovery RESTORE DB Execution
* **Prompt**:
  ```text
  Role:
  You are a Resilience Operations Manager responsible for incident response and disaster recovery of
  IBM Storage Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. Recovery is needed and I am signed in as mcp-svc-operator.

  Task:
  - Restore the SPSVR01 database from yesterday's backup.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Restore result.
  ```
* **Anti-Pattern**: Operator or policy administrator attempting to initiate full database restoration (`restore_db` requires `system` privilege).
* **Expected Defense**: Server rejects execution; destructive database restore strictly restricted to `system` privilege class.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR06ResilienceManager::test_np_r06_01_restore_db_privilege_denial`

### NP-R06-02: Set Client Lock with Malformed Lock State Enum
* **Prompt**:
  ```text
  Role:
  You are a Resilience Operations Manager responsible for incident response and disaster recovery of
  IBM Storage Protect.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. A node must be isolated quickly.

  Task:
  - Set client lock on DBSQL01_NODE with lock_status='QUARANTINE_DESTROY'.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Lock result.
  ```
* **Anti-Pattern**: Supplying an unsupported enum value for `lock_status` (valid values: `lock`, `unlock`).
* **Expected Defense**: Schema validation rejects unlisted enum before command execution.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR06ResilienceManager::test_np_r06_02_client_lock_invalid_enum`

---

## R-07 · Storage Protect Service Engineer — Negative Prompts

### NP-R07-01: Servermon Argument Injection
* **Prompt**:
  ```text
  Role:
  You are an IBM Storage Protect Service Engineer responsible for diagnostics and defect
  investigation.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I am gathering diagnostics for a support case.

  Task:
  - Run servermon with args ['-standard', '&& cat /etc/passwd'] to collect diagnostics and user
    lists.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Servermon output.
  ```
* **Anti-Pattern**: Shell chaining characters (`&&`, `|`, `;`) injected into Servermon arguments.
* **Expected Defense**: Arguments passed as array elements directly to `subprocess.Popen` without shell interpolation (`shell=False`); execution of injected shell code is impossible.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR07ServiceEngineer::test_np_r07_01_servermon_argument_shell_injection`

### NP-R07-02: Activity Log Search with Invalid Date Range Syntax
* **Prompt**:
  ```text
  Role:
  You are an IBM Storage Protect Service Engineer responsible for diagnostics and defect
  investigation.

  Context:
  IBM Storage Protect server SPSVR01, reached through the MCP server
  sp-mcp-server-remote-tumbleweed. I am searching for a known error message.

  Task:
  - Search the activity log for ANR0406E with begindate='INVALID_DATE_TOKEN'.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Matching log lines.
  ```
* **Anti-Pattern**: Non-date string passed to `begindate`.
* **Expected Defense**: Command formats string cleanly; SP backend CLI validation rejects invalid date with syntax error code; server reports error without crashing.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR07ServiceEngineer::test_np_r07_02_activity_log_invalid_date_syntax`

---

## R-08 · Multi-Server Replication & Data Management — Negative Prompts

### NP-R08-01: Cross-Server Ephemeral Session Replay
* **Prompt**:
  ```text
  Role:
  You are a Data Protection Administrator responsible for replication across a three-server IBM
  Storage Protect topology.

  Context:
  Three-server topology reached through MCP servers sp-mcp-spsvr01, sp-mcp-spsvr02, and
  sp-mcp-spsvr03. I hold an authenticated session lease obtained from SPSVR01.

  Task:
  - Reuse that lease to execute query_replication_rule on SPSVR02.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Replication rule list.
  ```
* **Anti-Pattern**: Replaying a valid session token across distinct target server boundaries.
* **Expected Defense**: `_check_session_target_server()` validates `SessionLease.target_server == requested_server`. Mismatches raise immediate `AUTHORIZATION_DENIED`.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR08Replication::test_np_r08_01_cross_server_session_replay_rejection`

### NP-R08-02: Query Replication Status Missing Required Node Name
* **Prompt**:
  ```text
  Role:
  You are a Data Protection Administrator responsible for replication across a three-server IBM
  Storage Protect topology.

  Context:
  Three-server topology reached through MCP servers sp-mcp-spsvr01, sp-mcp-spsvr02, and
  sp-mcp-spsvr03. I want a quick look at replication activity on SPSVR01.

  Task:
  - Query active replication status without specifying any node name.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Replication status.
  ```
* **Anti-Pattern**: Omitting mandatory parameter `node_name` on `query_replication_status`.
* **Expected Defense**: Tool pre-validates `arguments.get("node_name")` and immediately returns error message without sending invalid syntax to SP.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR08Replication::test_np_r08_02_query_replication_missing_node_name`

### NP-R08-03: Multi-Target Replication Rule Definition Violation
* **Prompt**:
  ```text
  Role:
  You are a Data Protection Administrator responsible for replication across a three-server IBM
  Storage Protect topology.

  Context:
  Three-server topology reached through MCP servers sp-mcp-spsvr01, sp-mcp-spsvr02, and
  sp-mcp-spsvr03. Replication to both remote servers should be defined in one place.

  Task:
  - Create a single replication storage rule REPL_RULE_ALL that replicates to both SPSVR02 and
    SPSVR03.

  Constraints:
  - Attempt exactly what is requested; do not rephrase it into a safer request.
  - Report the server response or error verbatim.

  Output Format:
  Rule definition result.
  ```
* **Anti-Pattern**: Attempting to specify multiple target servers in a single replication rule (IBM Storage Protect architecture allows only one target server per replication rule).
* **Expected Defense**: Architecture guideline enforcement or backend error reporting prevents rule creation with multiple targets.
* **Test Mapping**: `tests/test_sample_prompts_negative.py::TestNegativeR08Replication::test_np_r08_03_multi_target_replication_rule_violation`
