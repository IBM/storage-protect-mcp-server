# IBM Storage Protect MCP Server — System Architecture & Design

* **Revision**: 2026-09 (Post-Audit Remediation — AUD-07, AUD-08, DAUTH-7 Closed)
* **Cross-reference**: [`docs/analysis/security-design-analysis.md`](../analysis/security-design-analysis.md) · [`docs/traceability/gap-analysis.md`](../traceability/gap-analysis.md) · [`docs/traceability/audit-report.md`](../traceability/audit-report.md)
* **Source reference**: `src/sp_mcp_server/`

---

## 1. Overview & System Context

The IBM Storage Protect MCP Server provides a standardized Model Context Protocol (MCP) interface enabling AI agents and automated clients to interact with IBM Storage Protect (formerly Tivoli Storage Manager / Spectrum Protect) servers. 

The server provides natural language administration capabilities mapped directly onto native Storage Protect commands while preserving enterprise-grade access control, session security, secret masking, and comprehensive auditability.

The architecture provides two operating models:
1. **Unified MCP Server (`main.py`)**: Runs all or selected functional server groups in a single process over `stdio` or secure `http` SSE transport.
2. **Micro-MCP Servers (`main_<module>_*.py`)**: Fine-grained, isolated server processes (e.g., `main_clients_core.py`, `main_storage_pools.py`, `main_ops_protection.py`) optimized for LLM context window efficiency and least-privilege scoping.

---

## 2. Core Architectural Principles

1. **Strict Least Privilege & Separation of Concerns**:
   - Commands are partitioned into 5 administrative modules (`clients`, `storage`, `policies`, `system`, `operations`).
   - Every tool declares a `required_privilege` (`system`, `policy`, `storage`, `operator`, `any`).
   - In service-account mode, tool discovery queries the configured account's SP authority (`QUERY ADMIN <name> FORMAT=DETAILED`) and restricts tool registration accordingly.
   - Dynamic-session and OIDC privilege claims are enforced at invocation time via `_privilege_satisfies_for_session()` and `current_request_privilege` context variable checks in `handle_call_tool()`.
   - `_check_session_target_server()` enforces `SessionLease.target_server` binding immediately after privilege confirmation; cross-server session reuse is rejected with `AUTHORIZATION_DENIED` (DAUTH-7, closed).
   - Delegated session credentials are applied to command execution via `current_execution_credentials` context variable and cleared in the `finally` block.

2. **Defense-in-Depth Session & Transport Security**:
   - **Local Stdio Transport**: Secured via SSH Ed25519 key authentication, dedicated non-privileged OS user (`mcp-runner`), and explicit strict host key checking.
   - **Remote HTTP/SSE Transport**: Requires TLS 1.2+ certificates and OAuth 2.1 / OIDC Bearer Token authentication (`OIDCBearerMiddleware`) with call-time scope enforcement; per-scope privilege mapping (`mcp:*`) and `AUTHORIZATION_DENIED` rejection validated by `TestOIDCAuthorization` (7 scopes).
   - **Dynamic Authentication (Challenge-Response)**: Allows interactive AI chat users to receive structured `AUTHENTICATION_REQUIRED` responses, verifies credentials via zero-trace `execute_silent()`, issues bounded ephemeral leases, enforces lease privileges, applies delegated credentials to command execution, and supports explicit session revocation via `logout_session`.
   - **Session Lifecycle**: `SessionManager` uses `RLock` and bounds TTLs to `MAX_SESSION_TTL_SECONDS`. Cleanup is opportunistic (on create / explicit call). `SessionLease.password` is zeroed on every removal path — explicit revocation, inactivity/absolute TTL expiry, bulk sweep, and server shutdown (AUD-08, closed).
   - **Backend Storage Protect Channel**: `SESSIONSECURITY=STRICT` validated at startup; `dsm.sys` enforces `SSLREQUIRED Yes` and `PASSWORDACCESS GENERATE`. Service account provisioning script (`scripts/provision-sp-service-accounts.sh`) registers all five tiered accounts with `SESSIONSECURITY=STRICT` and `MFAREQUIRED=NO` (AUD-07, closed).

3. **Two-Person Integrity & Policy Controls**:
   - Destructive operations support IBM SP native Command Approval (`SET COMMANDAPPROVAL ON`, `APPROVE PENDINGCMD`, `REJECT PENDINGCMD`, `WITHDRAW PENDINGCMD`).
   - Password-bearing administrative operations pre-validate length against SP `MINPWLENGTH` and execute via silent channels without exposing plaintext passwords in logs or process arguments.

4. **Auditing & SIEM Traceability**:
   - Every write operation emits a traceable correlation marker into IBM Storage Protect Activity Log via `DEFINE SCRATCHPADENTRY MCP_AUDIT` (`POL-4`).

---

## 3. Layered System Architecture

```mermaid
graph TD
    subgraph ClientTier ["1. Client & Agent Layer"]
        AGENT["AI Agent / LLM Client\n(Claude Desktop, Cursor, IDE, Custom Agent)"]
    end

    subgraph IngressTier ["2. Ingress & Protocol Layer"]
        STDIO_EP["stdio Entry Point\n(Subprocess stdin/stdout over SSH)"]
        HTTP_EP["HTTP / SSE Entry Point\n(FastAPI / Uvicorn with TLS & OIDC Auth)"]
    end

    subgraph CoreTier ["3. MCP Server Core & Security Gates"]
        SEC_START["secure_startup()\n• .env POSIX 0600 permission check"]
        CONFIG_MGR["config.py: ServerConfig\n• 5-Tier Service Account Credentials\n• Keyring / Secrets Resolution"]
        SESS_MGR["session.py: SessionManager\n• Dynamic ephemeral leases (TTL=15m)\n• Zero-trace auth verification\n• Password zeroed on all removal paths (AUD-08)\n• logout_session explicit revocation tool\n• current_audit_user contextvar"]
        FACTORY["mcp_factory.py\n• _validate_session_security() (SESSIONSECURITY=STRICT)\n• _check_lockout_policy() (SET INVALIDPWLIMIT)\n• _parse_sp_privilege() (QUERY ADMIN)\n• Tool Privilege Filtering (_PRIVILEGE_SATISFIES)\n• _check_session_target_server() (DAUTH-7)\n• Tool Invocation & POL-4 ACTLOG Audit Attribution"]
    end

    subgraph ModuleTier ["4. Command & Tool Abstraction Layer"]
        GROUPS["server_groups.py\n• ISP_CLIENTS_* • ISP_STORAGE_* • ISP_POLICIES_*\n• ISP_SYSTEM_* • ISP_OPS_* • ISP_VOLUMES"]
        BASE_CMD["commands/base.py\n• BaseCommand (dsmadmc tools)\n• BaseOfflineCommand (dsmserv offline tools)\n• BaseServermonCommand (servermon diagnostic tools)"]
        IMPL_CMD["Command Implementations\n• commands/clients/ • commands/storage/\n• commands/policies/ • commands/system/\n• commands/operations/ • commands/offline.py • commands/servermon.py"]
    end

    subgraph WrapperTier ["5. CLI & Execution Wrapper Layer"]
        ADMC_WRAP["DsmAdmcWrapper\n• Stash authentication (PASSWORDACCESS GENERATE)\n• execute() & execute_silent() password masking"]
        SERV_WRAP["DsmServWrapper\n• sudo -u <instance_user> dsmserv execution"]
        MON_WRAP["ServermonWrapper\n• sudo -u <instance_user> servermon execution"]
    end

    subgraph StorageProtectTier ["6. IBM Storage Protect Server"]
        DSMADMC["dsmadmc (Port 1500, TLS 1.2/1.3)"]
        DSMSERV["dsmserv binary"]
        SERVERMON["servermon binary"]
        ACTLOG["Activity Log & Scratchpad Entries"]
    end

    AGENT -->|stdio| STDIO_EP
    AGENT -->|HTTP/SSE| HTTP_EP
    STDIO_EP --> SEC_START
    HTTP_EP --> SEC_START
    SEC_START --> FACTORY
    FACTORY --> SESS_MGR
    FACTORY --> CONFIG_MGR
    FACTORY --> GROUPS
    GROUPS --> BASE_CMD
    BASE_CMD --> IMPL_CMD
    IMPL_CMD --> ADMC_WRAP
    IMPL_CMD --> SERV_WRAP
    IMPL_CMD --> MON_WRAP
    ADMC_WRAP --> DSMADMC
    SERV_WRAP --> DSMSERV
    MON_WRAP --> SERVERMON
    DSMADMC --> ACTLOG
```

---

## 4. Server Startup & Security Lifecycle

When an MCP server process starts (either `main.py` or a specialized `main_*.py`), it executes a strict startup sequence:

```mermaid
sequenceDiagram
    participant OS as OS / Process Environment
    participant Main as Entry Point (main*.py)
    participant Config as config.py
    participant Factory as mcp_factory.py
    participant CLI as DsmAdmcWrapper
    participant SP as IBM Storage Protect Server

    OS->>Main: Launch Process
    Main->>Config: secure_startup(".env")
    note over Config: CRED-3 / RG-2: Check POSIX 0600 file permissions
    Config->>Config: check_env_file_permissions()
    alt Permissions too open (>0600)
        Config-->>OS: sys.exit(1)
    end
    Config->>Config: load_dotenv()
    
    Main->>Factory: create_mcp_server(name, tool_classes)
    Factory->>Config: load_config()
    Config-->>Factory: ServerConfig (credentials map)

    note over Factory: NET-1 / RG-1: Validate Session Security
    Factory->>CLI: execute("QUERY ADMIN <id> FORMAT=DETAILED")
    CLI->>SP: dsmadmc QUERY ADMIN (over TLS)
    SP-->>CLI: Output (Session Security: Strict)
    CLI-->>Factory: Result
    alt Session Security != Strict
        Factory-->>OS: sys.exit(1)
    end

    note over Factory: ACC-2: Query Administrator Privilege Class
    Factory->>Factory: _parse_sp_privilege() -> account_privilege
    Factory->>Factory: Filter tool_classes using _PRIVILEGE_SATISFIES

    note over Factory: POL-3: Check Account Lockout Policy
    Factory->>CLI: execute("QUERY STATUS")
    CLI-->>Factory: Status output (Invalid Sign-on Attempt Limit)

    Factory-->>Main: Ready Server instance
    Main->>Main: run_server() (stdio or HTTP/SSE)
```

---

## 5. Tool Execution & Audit Workflow

When an MCP client invokes a tool:

```mermaid
sequenceDiagram
    participant Client as MCP Client
    participant Server as MCP Server (handle_call_tool)
    participant BaseCmd as BaseCommand Subclass
    participant Wrapper as DsmAdmcWrapper
    participant SP as IBM Storage Protect Server

    Client->>Server: call_tool(name, arguments)
    Server->>Server: Verify tool exists and arguments match JSON Schema
    
    opt Write Operation (tool required_privilege in {system, policy, storage, operator})
        note over Server: POL-4: Audit Record Generation
        Server->>Wrapper: execute('DEFINE SCRATCHPADENTRY MCP_AUDIT DESCRIPTION="MCP_AUDIT tool=... corr=<uuid>"')
        Wrapper->>SP: dsmadmc DEFINE SCRATCHPADENTRY ...
        SP-->>Wrapper: OK / Error
        alt Audit write fails
            note over Server: RG-4: Log SECURITY [POL-4/RG-4] ERROR
        end
    end

    opt Password-Bearing Command (DefineAdmin, RegisterNode)
        note over BaseCmd: POL-2: Pre-validate password against MINPWLENGTH
        BaseCmd->>Wrapper: execute("QUERY OPTION MINPWLENGTH")
        Wrapper-->>BaseCmd: MINPWLENGTH value
    end

    Server->>BaseCmd: execute(arguments)
    alt Sensitive Command (Password / Secret)
        BaseCmd->>Wrapper: execute_silent(cmd)
    else Standard Command
        BaseCmd->>Wrapper: execute(cmd)
    end
    Wrapper->>SP: dsmadmc <command>
    SP-->>Wrapper: stdout, stderr, returncode
    Wrapper-->>BaseCmd: Output
    BaseCmd-->>Server: Result string
    Server-->>Client: TextContent(result)
```

---

## 6. Domain Breakdown & Micro-Servers

The codebase provides multiple dedicated Micro-MCP entry points categorized across 5 administrative modules, in addition to the unified server. Supported entry points use the atomic `secure_startup()` helper before loading configuration.

| Module Category | Micro-MCP Server Entry Point | Command Group | Focus & Administrative Scope |
| :--- | :--- | :--- | :--- |
| **Clients** | [`main_clients_core.py`](../../src/sp_mcp_server/main_clients_core.py)<br>[`main_clients_config.py`](../../src/sp_mcp_server/main_clients_config.py) | `ISP_CLIENTS_CORE`<br>`ISP_CLIENTS_CONFIG` | Node registration, locks, updates, renames, node groups, client option sets (`cloptset`), and schedule associations. |
| **Storage** | [`main_storage_pools.py`](../../src/sp_mcp_server/main_storage_pools.py)<br>[`main_storage_hardware.py`](../../src/sp_mcp_server/main_storage_hardware.py)<br>[`main_storage_device.py`](../../src/sp_mcp_server/main_storage_device.py)<br>[`main_volumes.py`](../../src/sp_mcp_server/main_volumes.py) | `ISP_STORAGE_POOLS`<br>`ISP_STORAGE_HARDWARE`<br>`ISP_STORAGE_DEVICE`<br>`ISP_VOLUMES` | Storage pools, directory containers, tape libraries, drives, paths, device classes, data movers, and volume history. |
| **Policies** | [`main_policies_lifecycle.py`](../../src/sp_mcp_server/main_policies_lifecycle.py)<br>[`main_policies_management.py`](../../src/sp_mcp_server/main_policies_management.py) | `ISP_POLICIES_LIFECYCLE`<br>`ISP_POLICIES_MANAGEMENT` | Policy domains, policy set validation/activation, management classes, copy groups, and retention schedules. |
| **System** | [`main_system_admin.py`](../../src/sp_mcp_server/main_system_admin.py)<br>[`main_system_config.py`](../../src/sp_mcp_server/main_system_config.py) | `ISP_SYSTEM_ADMIN`<br>`ISP_SYSTEM_CONFIG` | Admin accounts, authority granting, command approvals (`APPROVE PENDINGCMD`), server definitions, scripts, and cloud connections. |
| **Operations** | [`main_ops_protection.py`](../../src/sp_mcp_server/main_ops_protection.py)<br>[`main_ops_maintenance.py`](../../src/sp_mcp_server/main_ops_maintenance.py)<br>[`main_ops_rules.py`](../../src/sp_mcp_server/main_ops_rules.py) | `ISP_OPS_PROTECTION`<br>`ISP_OPS_MAINTENANCE`<br>`ISP_OPS_RULES` | DB backup/restore, DR media, replication, data movement, storage reclamation, automation rules, subrules, and alerts. |
| **Unified Server** | [`main.py`](../../src/sp_mcp_server/main.py) | Configurable via `--enable-servers` | Unified server combining all selected modules over stdio or HTTP. |

---

## 7. Security Design References

For domain-specific detailed security control specifications:
- [`docs/design/security-dynamic-authn.md`](../design/security-dynamic-authn.md) — Dynamic & Delegated User Authentication (Challenge-Response).
- [`docs/design/security-network.md`](../design/security-network.md) — Network Security, SSH Transport & TLS Enforcement.
- [`docs/design/security-identity-credentials.md`](../design/security-identity-credentials.md) — Tiered Credentials, Stash Mode & Keyring Integration.
- [`docs/design/security-access.md`](../design/security-access.md) — Tool Privilege Gating & Sudoers Execution.
- [`docs/design/security-policy.md`](../design/security-policy.md) — Command Approval, Password Policies & ACTLOG Audit Trail.
- [`docs/design/security-integrations.md`](../design/security-integrations.md) — OAuth 2.1 / OIDC HTTP Transport & Secrets Reference Resolution.
- [`docs/design/security-non-repudiation.md`](../design/security-non-repudiation.md) — Non-Repudiation, Activity Log Attribution & Forensic Correlation.

---

## 8. Directory Structure & Key Files

```
storage-protect-mcp-server/
├── pyproject.toml                     # Package dependencies, CLI entry points
├── src/sp_mcp_server/
│   ├── __init__.py                    # Package exports
│   ├── cli_wrapper.py                 # DsmAdmcWrapper, DsmServWrapper, ServermonWrapper
│   ├── config.py                      # ServerConfig, secure_startup(), credential resolution
│   ├── http_server.py                 # FastAPI / Starlette OIDC Bearer Token middleware
│   ├── mcp_factory.py                 # Core MCP server factory, security gates, audit logging
│   ├── server_groups.py               # Tool group definitions across all modules
│   ├── main.py                        # Unified server entry point (--enable-servers)
│   ├── main_*.py                      # Domain-specific and legacy micro-server entry points
│   └── commands/                      # Command implementations
│       ├── base.py                    # BaseCommand, BaseOfflineCommand, BaseServermonCommand
│       ├── offline.py                 # Offline DB/log tools (dsmserv)
│       ├── servermon.py               # Servermon diagnostic tools
│       ├── clients/                   # assoc.py, groups.py, info.py, node.py, opt.py
│       ├── storage/                   # content.py, datamover.py, device.py, drive.py, ...
│       ├── policies/                  # copy.py, domain.py, mgmt.py, policyset.py, ...
│       ├── system/                    # admin.py, auth.py (AuthenticateSession, LogoutSession), config.py, conn.py, logs.py, script.py, ...
│       └── operations/                # alerts.py, approval.py, backupset.py, catalog.py, ...
├── config/
│   └── dsm.sys.template               # dsmadmc client-options template (SSL Yes, SSLREQUIRED Yes, PASSWORDACCESS GENERATE)
├── scripts/
│   └── provision-sp-service-accounts.sh  # Idempotent SP service account provisioning (5 tiers, SESSIONSECURITY=STRICT)
├── tests/                             # Test suite
│   ├── test_cli_wrapper.py
│   ├── test_commands.py
│   ├── test_config.py
│   ├── test_core_components.py
│   └── test_security_controls.py      # Security regression tests — 88 tests passing post-remediation
└── docs/                              # Comprehensive documentation
    ├── design/                        # Domain-specific security design specifications
    ├── architecture/                  # System & module-specific architecture docs
    ├── analysis/                      # Security design analysis & gap closure validation
    ├── traceability/                  # Traceability matrix and gap analysis
    └── guides/                        # User, installation, configuration, and troubleshooting guides
```
