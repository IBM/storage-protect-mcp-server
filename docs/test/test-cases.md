# Test Case Catalog

* **Document**: Test Cases for IBM Storage Protect MCP Server
* **Revision**: 2026-10
* **Status**: Complete & Verified
* **Total Automated Tests Mapped**: **188 Test Cases** across 12 files
* **Inputs**: Architecture Docs, Security Design Specs, Implementation Specs, User Guides, Source Code (`src/sp_mcp_server/`), and Test Automation Suite (`tests/`)

---

## Catalog Index & Overview

| Section | Domain / Category | Automated Test File | Tests | Focus Area |
| :--- | :--- | :--- | :---: | :--- |
| **Section 1** | Startup & Security Invariants | [`tests/test_sec_startup.py`](../../tests/test_sec_startup.py) | 23 | NET-1, RG-1, CRED-3, RG-2, ACC-2, POL-3 |
| **Section 2** | Password Silent Execution | [`tests/test_sec_password_commands.py`](../../tests/test_sec_password_commands.py) | 13 | RG-3, CRED-2, Log sanitization |
| **Section 3** | Audit Trail & HTTP TLS | [`tests/test_sec_audit_trail.py`](../../tests/test_sec_audit_trail.py) | 8 | POL-4, RG-4, NR-1, NR-4, RG-5 |
| **Section 4** | Dynamic Authentication | [`tests/test_sec_dynamic_auth.py`](../../tests/test_sec_dynamic_auth.py) | 17 | DAUTH-1, DAUTH-2, DAUTH-4, DAUTH-5, INT-1, INT-2 |
| **Section 5** | Session Lifecycle & Server Binding | [`tests/test_sec_session_lifecycle.py`](../../tests/test_sec_session_lifecycle.py) | 14 | CRED-3b, DAUTH-3, DAUTH-7, DAUTH-8, DAUTH-9 |
| **Section 6** | OAuth 2 Extended Middleware | [`tests/test_sec_oauth2.py`](../../tests/test_sec_oauth2.py) | 26 | OA-1, OA-2, OA-4, OA-5, OA-6, OA-7 |
| **Section 7** | Subprocess CLI Wrapper | [`tests/test_cli_wrapper.py`](../../tests/test_cli_wrapper.py) | 5 | Subprocess quoting, exit codes, sudo execution |
| **Section 8** | Core Commands & Config | [`tests/test_commands.py`](../../tests/test_commands.py), [`tests/test_config.py`](../../tests/test_config.py) | 8 | BaseCommand queries, keyring resolution |
| **Section 9** | Core Components & Privilege | [`tests/test_core_components.py`](../../tests/test_core_components.py) | 7 | Sudo privilege escalation, offline commands |
| **Section 10** | Persona Prompt Scenarios (Unit) | [`tests/test_sample_prompts_positive.py`](../../tests/test_sample_prompts_positive.py) | 88 | Personas R-01..R-08 & Privilege annotations |
| **Section 11** | Live System Integration | [`tests/test_sample_prompts_positive.py`](../../tests/test_sample_prompts_positive.py) | 15 | Live SP server staging verification |

---

## Section 1: Startup & Security Invariants (`test_sec_startup.py` — 23 Tests)

### 1.1 `TestValidateSessionSecurity` (NET-1: Strict Session Security Enforcement)
* **Objective**: Ensure the MCP server unconditionally halts with `sys.exit(1)` at startup if any configured administrative account does not have `SESSIONSECURITY=Strict` or valid TLS transport.

| Case ID | Test Method | Input / Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-NET-01** | `test_exits_when_session_security_not_strict` | `QUERY STATUS` returns `SESSIONSECURITY=Transitional` | Server raises `SystemExit(1)`. Startup aborted. |
| **TC-NET-02** | `test_exits_when_query_fails` | `dsmadmc` returns returncode 1 (connection refused / timeout) | Server raises `SystemExit(1)`. Startup aborted. |
| **TC-NET-03** | `test_passes_when_strict_and_tls` | Output shows `SESSIONSECURITY=Strict` and `Transport Method=TLS 1.2/1.3` | Session security validation passes without exception. |
| **TC-NET-04** | `test_passes_when_strict_and_blank_transport` | Output shows `SESSIONSECURITY=Strict` and blank transport (legacy SP) | Accepted without exception; backward compatible. |
| **TC-NET-05** | `test_skip_flag_bypasses_check_non_production` | `SP_MCP_SKIP_SECURITY_CHECKS=1` in dev/test environment | Session check skipped with logged `WARNING`. |

### 1.2 `TestProductionGuard` (RG-1: Production Security Bypass Block)
* **Objective**: Block startup bypasses when running in production (`SP_MCP_ENV=production`).

| Case ID | Test Method | Input / Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-RG1-01** | `test_exits_when_skip_set_in_production` | `SP_MCP_SKIP_SECURITY_CHECKS=1` and `SP_MCP_ENV=production` | Server raises `SystemExit(1)`. Startup strictly blocked. |
| **TC-RG1-02** | `test_allows_skip_in_non_production` | `SP_MCP_SKIP_SECURITY_CHECKS=1` and `SP_MCP_ENV=test` | Startup allowed; logs warning. |
| **TC-RG1-03** | `test_allows_skip_with_no_env_set` | `SP_MCP_SKIP_SECURITY_CHECKS=1` and `SP_MCP_ENV` unset | Startup allowed; defaults to non-production. |

### 1.3 `TestEnvFilePermissions` & `TestSecureStartup` (CRED-3, RG-2: POSIX Permission Checks)
* **Objective**: Enforce strict `0600` permissions on `.env` files containing credentials.

| Case ID | Test Method | Input / Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-CRED3-01** | `test_rejects_world_readable_env` | `.env` file with mode `0644` (POSIX) | Raises `SystemExit(1)`. (Skipped on Windows). |
| **TC-CRED3-02** | `test_rejects_group_readable_env` | `.env` file with mode `0640` (POSIX) | Raises `SystemExit(1)`. (Skipped on Windows). |
| **TC-CRED3-03** | `test_accepts_owner_only_env` | `.env` file with mode `0600` | Permission check succeeds. |
| **TC-CRED3-04** | `test_accepts_missing_env` | Non-existent `.env` path | Passes cleanly (credentials may come from OS env). |
| **TC-RG2-01** | `test_secure_startup_rejects_insecure_env` | `secure_startup()` called on mode `0644` file | Raises `SystemExit(1)`. Atomic check and load aborts. |
| **TC-RG2-02** | `test_secure_startup_loads_env_when_permissions_ok` | `secure_startup()` called on mode `0600` file | Variables loaded into `os.environ` successfully. |

### 1.4 `TestPrivilegeFiltering` (ACC-2: Tier-Filtered Tool Registration)
* **Objective**: Ensure the MCP server registers only the tool subset matching the account's SP authority tier.

| Case ID | Test Method | Input / Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-ACC2-01** | `test_system_account_satisfies_all_tiers` | Account has SP privilege `system` | Registers all tools requiring `system`, `policy`, `storage`, `operator`, `any`. |
| **TC-ACC2-02** | `test_policy_account_satisfies_narrower_tiers` | Account has SP privilege `policy` | Registers tools requiring `policy`, `operator`, `any`. Excludes `system`, `storage`. |
| **TC-ACC2-03** | `test_storage_account_satisfies_narrower_tiers` | Account has SP privilege `storage` | Registers tools requiring `storage`, `operator`, `any`. Excludes `system`, `policy`. |
| **TC-ACC2-04** | `test_operator_account_satisfies_operator_and_any` | Account has SP privilege `operator` | Registers tools requiring `operator`, `any`. Excludes higher tiers. |
| **TC-ACC2-05** | `test_none_privilege_registers_any_only` | Account has no SP privilege class | Registers only read-only `any` query tools. |
| **TC-ACC2-06** | `test_server_registers_subset_for_operator` | Server initialized with operator creds | Tool count matches operator tier; system tools omitted. |

### 1.5 `TestLockoutPolicy` (POL-3: Startup Lockout Policy Audit)
* **Objective**: Audit SP server lockout policy at startup and emit actionable warnings if lockout protection is disabled.

| Case ID | Test Method | Input / Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-POL3-01** | `test_warns_when_lockout_zero` | `QUERY STATUS` reports `INVALIDPWLIMIT=0` | Emits `WARNING` log urging `SET INVALIDPWLIMIT 5`. |
| **TC-POL3-02** | `test_passes_when_lockout_positive` | `QUERY STATUS` reports `INVALIDPWLIMIT=5` | Passes silently with no warning log. |
| **TC-POL3-03** | `test_handles_unparseable_lockout_output` | Unparseable or blank `QUERY STATUS` | Emits `WARNING` advising manual verification. |

---

## Section 2: Password Silent Execution (`test_sec_password_commands.py` — 13 Tests)

* **Objective**: Validate RG-3 silent execution for all password-bearing SP commands. Passwords must never appear in logs or process argument lists.

| Case ID | Test Method | SP Command Tested | Assertion & Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-RG3-01** | `test_define_admin_uses_execute_silent` | `REGISTER ADMIN <user> <pass>` | `execute_silent()` invoked. Password absent from logs. |
| **TC-RG3-02** | `test_register_node_uses_execute_silent` | `REGISTER NODE <node> <pass> DOMAIN=...` | `execute_silent()` invoked. Plaintext password not logged. |
| **TC-RG3-03** | `test_update_user_with_password_uses_execute_silent` | `UPDATE ADMIN <user> <pass>` | `execute_silent()` invoked when password provided. |
| **TC-RG3-04** | `test_update_user_without_password_uses_execute` | `UPDATE ADMIN <user> CONTACT="..."` | Standard `execute()` invoked (no password present). |
| **TC-RG3-05** | `test_update_node_with_password_uses_execute_silent` | `UPDATE NODE <node> <pass>` | `execute_silent()` invoked when updating password. |
| **TC-RG3-06** | `test_update_node_without_password_uses_execute` | `UPDATE NODE <node> DOMAIN=...` | Standard `execute()` invoked when updating metadata only. |
| **TC-RG3-07** | `test_define_server_uses_execute_silent` | `DEFINE SERVER <srv> PASSWORD=...` | `execute_silent()` invoked. Server password omitted from logs. |
| **TC-RG3-08** | `test_update_server_with_password_uses_execute_silent` | `UPDATE SERVER <srv> PASSWORD=...` | `execute_silent()` invoked when password provided. |
| **TC-RG3-09** | `test_update_server_without_password_uses_execute` | `UPDATE SERVER <srv> HLADDRESS=...` | Standard `execute()` invoked when updating address only. |
| **TC-RG3-10** | `test_define_data_mover_uses_execute_silent` | `DEFINE DATAMOVER ... PASSWORD=...` | `execute_silent()` invoked. Data mover password omitted from logs. |
| **TC-RG3-11** | `test_update_data_mover_with_password_uses_execute_silent` | `UPDATE DATAMOVER ... PASSWORD=...` | `execute_silent()` invoked when updating data mover password. |
| **TC-RG3-12** | `test_update_data_mover_without_password_uses_execute` | `UPDATE DATAMOVER ... HLADDRESS=...` | Standard `execute()` invoked when updating address only. |
| **TC-RG3-13** | `test_redact_command_masks_passwords` | Multiple dsmadmc commands | `_redact_command()` masks `PASSWORD=***` and positional passwords. |

---

## Section 3: Audit Trail & Transport Security (`test_sec_audit_trail.py` — 8 Tests)

### 3.1 `TestAuditTrail` (POL-4, RG-4, NR-1, NR-4: ACTLOG Scratchpad Attribution)
* **Objective**: Verify that write operations emit an audit correlation record to IBM Storage Protect ACTLOG via `DEFINE SCRATCHPADENTRY MCP_AUDIT` before executing.

| Case ID | Test Method | Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-POL4-01** | `test_scratchpad_entry_called_before_write` | Write tool (`delete_admin`) invoked | `DEFINE SCRATCHPADENTRY MCP_AUDIT` executed prior to command. Contains user, tool, privilege, correlation ID. |
| **TC-POL4-02** | `test_audit_write_failure_logs_error` | SP returns returncode 1 on scratchpad write | Logs `ERROR` with `SECURITY [POL-4 / RG-4 / NR-4]` marker. Write proceeds (fail-open mode). |
| **TC-POL4-03** | `test_strict_audit_fail_closed_aborts_execution` | `SP_MCP_STRICT_AUDIT=1` and scratchpad write fails | Tool execution aborted. Returns error: `Strict audit failure`. Target command never invoked. |

### 3.2 `TestHttpTransportTLS` (RG-5: HTTP Transport TLS Enforcement)
* **Objective**: Verify that `--transport http` strictly terminates without valid TLS certificate and private key.

| Case ID | Test Method | Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-RG5-01** | `test_http_transport_exits_without_tls_env_vars` | `SP_TLS_CERT` and `SP_TLS_KEY` unset | Process raises `SystemExit(1)` with `SECURITY [RG-5]`. |
| **TC-RG5-02** | `test_http_transport_exits_when_cert_missing` | `SP_TLS_CERT` points to non-existent file | Process raises `SystemExit(1)`. |
| **TC-RG5-03** | `test_http_transport_exits_when_key_missing` | `SP_TLS_KEY` points to non-existent file | Process raises `SystemExit(1)`. |
| **TC-RG5-04** | `test_http_transport_passes_with_valid_tls_files` | Valid cert and key files configured | TLS configuration succeeds; startup continues. |
| **TC-RG5-05** | `test_plaintext_flag_allows_http_without_tls_in_test` | `SP_MCP_ALLOW_HTTP_PLAINTEXT=1` | Allowed in test environment; logs high-visibility `ERROR`. |

---

## Section 4: Dynamic & Delegated Authentication (`test_sec_dynamic_auth.py` — 17 Tests)

### 4.1 `TestDynamicAuthentication` (DAUTH-1, DAUTH-2, DAUTH-4, DAUTH-5)
* **Objective**: Validate challenge-response authentication, session token leasing, and call-time privilege checks.

| Case ID | Test Method | Input / Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-DAUTH-01** | `test_dynamic_auth_challenge_when_unauthenticated` | Tool called with no session credentials | Returns JSON error: `error_type=AUTHENTICATION_REQUIRED`, structured challenge schema. |
| **TC-DAUTH-02** | `test_authenticate_session_tool_valid_credentials` | Valid admin ID and password submitted | Session minted. Returns `session_id`, `expires_in_seconds`, `sp_privilege`. Password not logged. |
| **TC-DAUTH-03** | `test_authenticate_session_tool_invalid_credentials` | Invalid password submitted to SP | Returns `AUTHENTICATION_FAILED`. Bad credentials omitted from log output. |
| **TC-DAUTH-04** | `test_dynamic_auth_executes_when_session_authenticated` | Valid `session_id` provided in tool arguments | Tool executes under authenticated session context. |
| **TC-DAUTH-05** | `test_dynamic_auth_denies_insufficient_privilege` | Operator session attempts system tool (`delete_admin`) | Returns `AUTHORIZATION_DENIED` before executing command. |
| **TC-DAUTH-06** | `test_session_ttl_is_bounded` | Configured session TTL | Lease expires strictly after `SP_MCP_SESSION_TTL` seconds. |
| **TC-DAUTH-07** | `test_static_mode_does_not_challenge` | Server configured in `service_account` mode | Tool executes directly using configured service account without challenge. |

### 4.2 `TestDelegatedSubprocess` (DAUTH-6, DAUTH-7)
* **Objective**: Verify that delegated session credentials are submitted to subprocesses via `execute_silent()` and scrubbed immediately from memory.

| Case ID | Test Method | Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-DAUTH-08** | `test_delegated_credentials_passed_to_subprocess` | Tool execution with active session | Subprocess invoked with session `-ID=` and `-PA=`. |
| **TC-DAUTH-09** | `test_execution_credentials_cleared_after_success` | Tool execution completes successfully | `current_execution_credentials` ContextVar reset to `None` in `finally` block. |
| **TC-DAUTH-10** | `test_execution_credentials_cleared_after_failure` | Tool execution raises runtime exception | `current_execution_credentials` ContextVar reset to `None` in `finally` block. |

### 4.3 `TestOIDCAuthorization` (INT-1, INT-2: Scope-to-Privilege Mapping)
* **Objective**: Verify OIDC token scope enforcement and request privilege gating at tool invocation time.

| Case ID | Test Method | Scope in Token | Permitted / Denied Operations |
| :--- | :--- | :--- | :--- |
| **TC-OIDC-01** | `test_oidc_scope_system_allows_system_tool` | `sp:system` | Permits system, policy, storage, operator, and query tools. |
| **TC-OIDC-02** | `test_oidc_scope_policy_allows_policy_tool` | `sp:policy` | Permits policy and operator tools. Rejects system tools. |
| **TC-OIDC-03** | `test_oidc_scope_storage_allows_storage_tool` | `sp:storage` | Permits storage tools. Rejects policy/system tools. |
| **TC-OIDC-04** | `test_oidc_scope_operator_denies_policy_tool` | `sp:operator` | Rejects policy tool with `AUTHORIZATION_DENIED`. |
| **TC-OIDC-05** | `test_oidc_scope_readonly_denies_write_tool` | `sp:readonly` | Rejects write tools (`delete_admin`). |
| **TC-OIDC-06** | `test_oidc_unmapped_scope_denies_all_tools` | `custom:scope` | Rejects all tools with `AUTHORIZATION_DENIED`. |
| **TC-OIDC-07** | `test_oidc_missing_scope_denies_tools` | No scope claim | Rejects tool calls with `AUTHORIZATION_DENIED`. |

---

## Section 5: Session Lifecycle & Target Server Binding (`test_sec_session_lifecycle.py` — 14 Tests)

### 5.1 `TestEntryPointStartup` (CRED-3b: Entry Point Permission Scan)
* **Objective**: Verify that all 26 entry point scripts (`main.py` + 25 `main_*.py`) call `secure_startup()` at initialization.

| Case ID | Test Method | Tested Target | Assertion |
| :--- | :--- | :--- | :--- |
| **TC-CRED3b-01** | `test_all_entry_points_call_secure_startup` | AST scan across all 26 entry points | Every script imports and invokes `secure_startup()`. |

### 5.2 `TestSessionCredentialLifecycle` (DAUTH-8, DAUTH-9: Memory Zeroing & Revocation)
* **Objective**: Ensure session passwords are overwritten in memory on all removal paths (explicit logout, expiration, clearing).

| Case ID | Test Method | Trigger | Assertion |
| :--- | :--- | :--- | :--- |
| **TC-DAUTH-11** | `test_logout_session_revokes_lease` | `logout_session` tool invoked | Session invalidated immediately. |
| **TC-DAUTH-12** | `test_logout_session_zeros_password` | Session logout | Underlying `SessionLease.password` cleared. |
| **TC-DAUTH-13** | `test_revoke_session_zeros_password` | Explicit `revoke_session(id)` | Password zeroed in memory. |
| **TC-DAUTH-14** | `test_cleanup_expired_zeros_passwords` | Background TTL cleanup sweep | Expired lease passwords zeroed. |
| **TC-DAUTH-15** | `test_clear_zeros_all_passwords` | `SessionManager.clear()` | All active lease passwords zeroed. |
| **TC-DAUTH-16** | `test_get_expired_session_zeros_and_revokes` | Accessing expired session | Zeroed and removed on demand. |
| **TC-DAUTH-17** | `test_session_manager_thread_safety` | Concurrent multi-threaded access | Synchronized via internal `RLock`. |

### 5.3 `TestTargetServerBinding` (DAUTH-7: Cross-Server Reuse Rejection)
* **Objective**: Verify that sessions minted for one Storage Protect server cannot be replayed against another server.

| Case ID | Test Method | Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-DAUTH-18** | `test_matching_target_server_passes` | `session.target_server == config.server_address` | Check passes; tool executes. |
| **TC-DAUTH-19** | `test_mismatched_target_server_rejected` | Session minted for `spsvr01`, tool points to `spsvr02` | Returns `AUTHORIZATION_DENIED`. Command aborted. |
| **TC-DAUTH-20** | `test_session_without_target_server_rejected` | Session object missing `target_server` | Returns `AUTHORIZATION_DENIED`. |
| **TC-DAUTH-21** | `test_server_case_insensitive_matching` | `SPSVR01.CORP` vs `spsvr01.corp` | Passes successfully (case-insensitive match). |
| **TC-DAUTH-22** | `test_target_server_port_matching` | Port included in server target | Normalized and matched correctly. |
| **TC-DAUTH-23** | `test_null_config_server_rejects_bound_session` | Server address unconfigured | Rejects with `AUTHORIZATION_DENIED`. |

---

## Section 6: OAuth 2 Extended Middleware (`test_sec_oauth2.py` — 26 Tests)

### 6.1 `TestOAuthASMetadata` (OA-1: RFC 8414 AS Metadata Proxy)
* **Objective**: Proxy IdP authorization server metadata at `/.well-known/oauth-authorization-server`.

| Case ID | Test Method | Assertion |
| :--- | :--- | :--- |
| **TC-OA1-01** | `test_fetch_as_metadata_returns_required_fields` | Contains `issuer`, `token_endpoint`, `jwks_uri`, `response_types_supported`. |
| **TC-OA1-02** | `test_as_metadata_cache_prevents_second_idp_call` | Second call within TTL served from memory cache; no outbound HTTP call. |
| **TC-OA1-03** | `test_as_metadata_cache_refreshes_after_ttl` | Cache refreshed after TTL expiration. |
| **TC-OA1-04** | `test_as_metadata_includes_s256_challenge_method` | Advertises `code_challenge_methods_supported: ["S256"]`. |

### 6.2 `TestJWKSRotation` (OA-2: JWKS TTL Cache & Rate Limiting)
* **Objective**: Rotate signing keys, cache JWKS within TTL, and protect against kid-miss cache stampede.

| Case ID | Test Method | Assertion |
| :--- | :--- | :--- |
| **TC-OA2-01** | `test_jwks_cached_within_ttl` | Outbound JWKS fetch performed once within TTL duration. |
| **TC-OA2-02** | `test_jwks_refreshed_after_ttl_expiry` | JWKS re-fetched upon token evaluation after TTL expiry. |
| **TC-OA2-03** | `test_kid_miss_triggers_one_refetch` | Unrecognized `kid` in token triggers immediate on-demand key refresh. |
| **TC-OA2-04** | `test_kid_miss_rate_limited_to_one_refetch` | Repeated invalid `kid` tokens rate-limited to 1 refresh per 60 seconds (anti-DoS). |

### 6.3 `TestPKCECapability` (OA-4: Startup PKCE Capability Audit)
* **Objective**: Audit IdP discovery metadata at startup to ensure PKCE `S256` support is advertised.

| Case ID | Test Method | Condition | Expected Behavior |
| :--- | :--- | :--- | :--- |
| **TC-OA4-01** | `test_s256_supported_logs_info_not_warning` | IdP advertises `S256` | Logs `INFO` message confirming PKCE support. |
| **TC-OA4-02** | `test_missing_s256_emits_warning` | IdP omits `S256` | Emits `WARNING` log advising IdP configuration. |
| **TC-OA4-03** | `test_plain_method_emits_warning` | IdP advertises insecure `plain` PKCE | Emits `WARNING` log warning against plain PKCE. |
| **TC-OA4-04** | `test_idp_unreachable_logs_warning_not_exception` | IdP endpoint unreachable at startup | Logs `WARNING` and allows startup (fail-open startup). |

### 6.4 `TestIntrospection` (OA-5: RFC 7662 Token Introspection)
* **Objective**: Perform token introspection against IdP to support immediate revocation checks.

| Case ID | Test Method | Assertion |
| :--- | :--- | :--- |
| **TC-OA5-01** | `test_revoked_token_returns_false` | IdP returns `{"active": false}`; request rejected with 401. |
| **TC-OA5-02** | `test_active_token_returns_true` | IdP returns `{"active": true}`; request accepted. |
| **TC-OA5-03** | `test_long_lived_token_skips_introspection` | Token TTL > threshold skips introspection (performance optimization). |
| **TC-OA5-04** | `test_introspection_fail_open` | Network failure during introspection fails open if local JWT validation passed. |
| **TC-OA5-05** | `test_missing_client_secret_skips_introspection` | Introspection omitted cleanly when client secret is unconfigured. |

### 6.5 `TestProtectedResourceMetadata` (OA-6: RFC 9470 Resource Metadata)
* **Objective**: Serve RFC 9470 metadata at `/.well-known/oauth-protected-resource` and inject `resource_metadata` into `WWW-Authenticate`.

| Case ID | Test Method | Assertion |
| :--- | :--- | :--- |
| **TC-OA6-01** | `test_protected_resource_doc_contains_required_fields` | Document returns `resource`, `authorization_servers`, `scopes_supported`. |
| **TC-OA6-02** | `test_protected_resource_doc_uses_public_url_as_resource` | Uses configured `SP_MCP_PUBLIC_URL` as the canonical resource identifier. |
| **TC-OA6-03** | `test_protected_resource_doc_falls_back_to_issuer` | Falls back to server address when public URL unset. |
| **TC-OA6-04** | `test_unauthorized_includes_resource_metadata_uri_when_public_url_set` | 401 response header contains `WWW-Authenticate: Bearer resource_metadata="..."`. |
| **TC-OA6-05** | `test_unauthorized_no_resource_metadata_when_public_url_absent` | 401 header omits `resource_metadata` parameter when public URL unset. |

### 6.6 `TestAuthModelAudit` (OA-7: Cross-Model Attribution in ACTLOG)
* **Objective**: Stamp `authmodel=` into every `DEFINE SCRATCHPADENTRY MCP_AUDIT` record to distinguish authentication paths.

| Case ID | Test Method | Auth Model Exercised | Expected ACTLOG String |
| :--- | :--- | :--- | :--- |
| **TC-OA7-01** | `test_local_authmodel_in_actlog` | Local stdio execution | `MCP_AUDIT ... authmodel=local ...` |
| **TC-OA7-02** | `test_client_credentials_authmodel_in_actlog` | Service-to-service client credentials token | `MCP_AUDIT ... authmodel=client_credentials ...` |
| **TC-OA7-03** | `test_oidc_bearer_authmodel_in_actlog` | Interactive user OIDC bearer token | `MCP_AUDIT ... authmodel=oidc_bearer ...` |
| **TC-OA7-04** | `test_dynamic_session_authmodel_set_after_authenticate` | Ephemeral leased session | `MCP_AUDIT ... authmodel=dynamic_session ...` |

---

## Section 7: Subprocess CLI Wrapper (`test_cli_wrapper.py` — 5 Tests)

* **Objective**: Verify command-line assembly, argument quoting, and sudo privilege escalation in `DsmAdmcWrapper`.

| Case ID | Test Method | Assertion |
| :--- | :--- | :--- |
| **TC-CLI-01** | `test_admc_wrapper_executes_successfully` | Valid stdout and returncode 0 returned from subprocess. |
| **TC-CLI-02** | `test_admc_wrapper_handles_command_failure` | Non-zero exit code captured and formatted into stderr error string. |
| **TC-CLI-03** | `test_admc_wrapper_quotes_parameters` | Parameters with whitespace quoted with double quotes (`-param="foo bar"`). |
| **TC-CLI-04** | `test_admc_wrapper_omits_password_when_stash_active` | `-PA=` omitted from subprocess arguments when `use_password_stash=True`. |
| **TC-CLI-05** | `test_admc_wrapper_injects_server_stanza` | `-se=<stanza>` injected when `server_name` is set. |

---

## Section 8: Core Commands & Config (`test_commands.py`, `test_config.py` — 8 Tests)

* **Objective**: Test base command execution and keyring password resolution.

| Case ID | Test Method | Assertion |
| :--- | :--- | :--- |
| **TC-CMD-01** | `test_base_command_execution` | `BaseCommand._execute_simple_query()` returns expected stdout. |
| **TC-CMD-02** | `test_base_command_error_formatting` | Returns standardized `Error executing command: <detail>` on failure. |
| **TC-CMD-03** | `test_command_requires_privilege_attribute` | Concrete command class without `required_privilege` raises error. |
| **TC-CMD-04** | `test_command_validation_helper` | `_validate_password_policy()` enforces `MINPWLENGTH`. |
| **TC-CFG-01** | `test_load_config_reads_env_vars` | `TCPSERVERADDRESS` and credentials loaded into `ServerConfig`. |
| **TC-CFG-02** | `test_load_config_supports_sp_server_address_alias` | Fallback alias `SP_SERVER_ADDRESS` successfully populates `server_address`. |
| **TC-CFG-03** | `test_keyring_password_resolution` | `_get_password()` queries OS keyring before falling back to `.env`. |
| **TC-CFG-04** | `test_credential_for_privilege_hierarchy` | `credential_for()` walks hierarchy down to `any` to find narrowest credential. |

---

## Section 9: Core Components & Privilege Escalation (`test_core_components.py` — 7 Tests)

* **Objective**: Test non-root `sudo -u` privilege escalation for offline commands (`dsmserv`, `servermon`).

| Case ID | Test Method | Assertion |
| :--- | :--- | :--- |
| **TC-CORE-01** | `test_dsmserv_wrapper_uses_sudo` | `DsmServWrapper` executes via `sudo -u <instance_user> -- dsmserv`. |
| **TC-CORE-02** | `test_servermon_wrapper_uses_sudo` | `ServermonWrapper` executes via `sudo -u <instance_user> -- servermon`. |
| **TC-CORE-03** | `test_offline_command_rejects_missing_binary` | Non-existent binary path raises descriptive error before execution. |
| **TC-CORE-04** | `test_server_groups_least_privilege` | Predefined server groups register only their declared domain tools. |
| **TC-CORE-05** | `test_server_groups_composite_mode` | Composite server combines multiple domain groups without namespace collision. |
| **TC-CORE-06** | `test_logging_setup_utc_format` | Log records formatted with ISO 8601 UTC timestamps (`%Y-%m-%dT%H:%M:%SZ`). |
| **TC-CORE-07** | `test_mcp_factory_reset_execution_state` | `reset_execution_state()` resets all 5 ContextVars, globals, and session caches. |

---

## Section 10: Persona Prompt Scenarios (`test_sample_prompts_positive.py` Part 1 — 88 Tests)

* **Objective**: Validate LLM user prompt templates, command syntax construction, and multi-step tool calls across all eight operational personas defined in [`docs/example/sample-prompts.md`](../example/sample-prompts.md).
* **Test Harness**: `tests/test_sample_prompts_positive.py` (Part 1) utilizing `FakeAdmcCli` and `FakeServermonCli` mock harnesses.

### 10.1 Persona R-01: Data Protection Operator (21 Tests)
* **Classes**: `TestR01DiscoveryAndStatus` (5), `TestR01BackupPolicyAndScheduling` (6), `TestR01NodeLifecycle` (6), `TestR01StoragePoolConfiguration` (4).
* **Test Focus**: Daily health checks, backup failure triage, client session queries, drive/path validation, storage pool utilization diagnostics, schedule association checks, node registration/renaming/locking.

### 10.2 Persona R-02: Data Protection Administrator (6 Tests)
* **Classes**: `TestR02PerformanceTuning` (2), `TestR02DatabaseDiagnostics` (2), `TestR02OperationalAudit` (2).
* **Test Focus**: Database buffer pool optimization (`TXNGROUPMAX`, `MOVEBATCHSIZE`), recovery log space analysis (`QUERY LOG` standard/detailed), storage reclamation tuning, 7-day schedule miss history (`QUERY EVENT`), inactive node occupancy inspection (`QUERY OCCUPANCY`).

### 10.3 Persona R-03: Infrastructure Solution Architect (4 Tests)
* **Classes**: `TestR03EnvironmentAndSizing` (4).
* **Test Focus**: Storage container deduplication efficiency (`QueryDeduplicationStats`), cloud/tape tier device class inspection (`QueryDeviceType`), container storage pool directory expansion (`DefineStoragePoolDirectory`), and enterprise license compliance auditing (`QueryLicenseInfo`).

### 10.4 Persona R-04: Workload & Application Owner (3 Tests)
* **Classes**: `TestR04WorkloadBackupIntegration` (3).
* **Test Focus**: Application-consistent backup volume file space validation for database nodes (`QueryClientBackupVolume`), SAP redo-log archive retention copy group definitions (`DefineCopyGroup`), and Oracle database data occupancy inspection (`QueryDataOccupancy`).

### 10.5 Persona R-05: Security & Compliance Officer (10 Tests)
* **Classes**: `TestR05SecurityHardening` (6), `TestR05PolicyAudit` (4).
* **Test Focus**: `SESSIONSECURITY=STRICT` compliance audit, dual-custody command approval workflow (`APPROVE PENDINGCMD`), password lockout enforcement, ACTLOG scratchpad forensic extraction, policy domain retention inspection, and management class listing.

### 10.6 Persona R-06: Resilience Operations Manager (4 Tests)
* **Classes**: `TestR06ResilienceOperations` (4).
* **Test Focus**: Suspected ransomware node isolation via client lock (`SetClientLock`), server database disaster recovery restore invocation (`RestoreDB`), disaster recovery plan file status queries (`QueryRecoveryPlanFile`), and offsite media tracking (`QueryDRMedia`).

### 10.7 Persona R-07: Storage Protect Service Engineer (3 Tests)
* **Classes**: `TestR07ServiceEngineerDiagnostics` (3).
* **Test Focus**: Servermon diagnostic utility invocation with custom flags (`RunServerMon`), activity log defect triage for specific message codes (`QueryActivityLog` with `SEARCH=ANR0406E`), and cloud migration warning frequency analysis (`QueryActivityLog` with `SEARCH=ANR8468W`).

### 10.8 Persona R-08: Multi-Server Replication & Data Management (7 Tests)
* **Classes**: `TestR08MultiServerReplication` (7).
* **Test Focus**: Multi-server replication topology discovery (`QueryReplicationServer`), cross-server storage replication rules (`QueryReplicationRule`), inbound/outbound replication failure record retrieval (`QueryReplicationFailures`), per-node replication progress monitoring (`QueryReplicationStatus`), storage pool synchronization verification (`QueryProtectionStatus`), failover node domain updating (`UpdateNode`), and storage tiering rule queries (`QueryStorageRule`).

### 10.9 Tool Type and Privilege Annotations (30 Tests)
* **Classes**: `TestPromptToolPrivilegeAnnotations` (18 read-only tool type tests + 12 write tool privilege tier tests).
* **Test Focus**: Ensures all tools referenced across the sample prompts are strictly annotated with correct access tiers (`read-only` vs. required privilege `policy`, `operator`, `storage`, `system`), guaranteeing zero privilege leaks.

### 10.10 Negative Persona Sample Prompts (`test_sample_prompts_negative.py` — 18 Tests: NP-R01-01 through NP-R08-03)
* **Catalog Reference**: [`tests/negative_sample_prompts.md`](../../tests/negative_sample_prompts.md)
* **Classes**:
  - `TestNegativeR01Operator` (3): Unbounded activity log dump prompt, operator storage pool deletion privilege denial, short password registration rejection.
  - `TestNegativeR02Administrator` (2): Out-of-bounds server option update, malformed session ID type.
  - `TestNegativeR03Architect` (2): Directory path traversal in storage pool expansion, non-existent pool deduplication query.
  - `TestNegativeR04WorkloadOwner` (2): Command injection inside client node name parameter, invalid copy group target pool.
  - `TestNegativeR05SecurityOfficer` (2): Dual-custody self-approval rejection, operator account attempting admin user lock.
  - `TestNegativeR06ResilienceManager` (2): Unprivileged disaster recovery `RESTORE DB` denial, client lock malformed enum handling.
  - `TestNegativeR07ServiceEngineer` (2): Servermon argument array injection defense, activity log invalid date syntax handling.
  - `TestNegativeR08Replication` (3): Cross-server session replay rejection, query replication missing mandatory node name, multi-target replication rule constraint.

---

## Section 11: Live System Integration (`test_sample_prompts_positive.py` Part 2 — 15 Tests)

* **Objective**: Execute end-to-end operational scenarios against a live IBM Storage Protect test server when staging credentials are provided.

| Case ID | Test Class | Methods | Operational Focus |
| :--- | :--- | :---: | :--- |
| **TC-INT-01..04** | `TestIntR01DiscoveryAndStatus` | 4 | Real `QUERY STATUS`, `QUERY SESSION`, `QUERY LOG` against live server. |
| **TC-INT-05..07** | `TestIntR01PolicyAndNodes` | 3 | Real client node query, occupancy analysis, policy set inspection. |
| **TC-INT-08..10** | `TestIntR02AdminDiagnostics` | 3 | Real DB utilization, storage pool threshold check, volume query. |
| **TC-INT-11..15** | `TestIntR05SecurityAudit` | 5 | Real admin account session security audit, pending approvals check, scratchpad write test. |

---

## Section 12: Negative Test Cases (NEG-01 to NEG-25)

* **Objective**: Validate that the server reliably and fail-closed rejects malformed protocol frames, privilege boundary violations, token tampering, dual-custody bypasses, and injection payloads without stack trace disclosure, memory corruption, or backend compromise.
* **Test Harness**: Containerized test-bed environment using `tests/test_sec_negative.py` and mock CLI fixtures.

### 12.1 Protocol, Framing & Schema Invalidation

| Case ID | Scenario / Negative Vector | Injected Input / Payload | Expected Error / Response | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **NEG-01** | Malformed JSON-RPC Syntax | Unclosed JSON payload: `{"jsonrpc": "2.0", "method": "tools/call"` | HTTP 400 or JSON-RPC `-32700 Parse error`; server connection remains stable. | Strict RFC 7159 JSON parsing |
| **NEG-02** | Missing JSON-RPC Framing Fields | Payload missing `jsonrpc` or `id` attributes: `{"method": "tools/call"}` | JSON-RPC `-32600 Invalid Request` returned; no command dispatched. | JSON-RPC 2.0 Compliance |
| **NEG-03** | Missing Mandatory Tool Parameters | `query_actlog` invoked without mandatory `search_string` or time window arguments. | JSON-RPC `-32602 Invalid params` with field violation detail; zero subprocesses spawned. | Pydantic Schema Validation |
| **NEG-04** | Parameter Type Incompatibility | Integer passed where dictionary expected; array passed for scalar `node_name`: `{"node_name": ["NODE1", "NODE2"]}` | Strict validation rejection before CLI wrapper layer; no execution. | Strong Type Safety |
| **NEG-05** | Oversized Payload / String Fuzzing | 10MB continuous string passed in parameter argument. | Request rejected or truncated fail-closed; memory consumption clamped; no OOM crash. | Resource DoS Protection |
| **NEG-06** | Unknown Tool Dispatch | Tool name `execute_arbitrary_shell` dispatched to server. | JSON-RPC `-32601 Method not found`; rejection without subprocess creation. | Closed Registry Boundary |

### 12.2 Security Boundaries & Privilege Abuse

| Case ID | Scenario / Negative Vector | Injected Input / Payload | Expected Error / Response | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **NEG-07** | Privilege Tier Escalation Attempt | Caller authenticated as `operator` invokes `halt_server` or `define_domain` (System tier). | Rejection with `AUTHORIZATION_DENIED`; failure logged to ACTLOG; command blocked. | ACC-1, ACC-2 |
| **NEG-08** | Micro-MCP Cross-Domain Bypass | Client connects to `clients` micro-MCP server and attempts to call `query_storagepool`. | Tool lookup fails (`Method not found` / unregistered tool); micro-MCP scope enforced. | Least Privilege Scoping |
| **NEG-09** | Unauthenticated Tool Invocation | Tool invocation sent to SSE/HTTP transport without `Authorization: Bearer` header. | HTTP 401 Unauthorized with `WWW-Authenticate: Bearer realm="sp-mcp"`. | NET-1, INT-1 |
| **NEG-10** | Cross-Server Target Replay | Dynamic session leased for `SERVER_PROD_01` used in request targeting `SERVER_DR_02`. | `_check_session_target_server` detects mismatch; raises `PermissionError`. | DAUTH-10 Target Server Binding |
| **NEG-11** | Expired Session Token Reuse | Tool invocation using session ID after lease TTL has elapsed. | Session lookup returns expired; rejected with `SESSION_EXPIRED` (HTTP 401 / MCP error). | DAUTH-4 Ephemeral Leases |
| **NEG-12** | Revoked Session Token Reuse | Tool invocation using session ID immediately after `delete_session` invocation. | Session table lookup fails; rejected with `INVALID_SESSION`; credentials zeroed. | DAUTH-9 Credential Zeroing |
| **NEG-13** | Non-Interactive MFA Escalation Bypass | Low-privilege session attempts to assume System tier without completing secondary challenge. | Challenge prompt returned; execution denied until valid response received. | CRED-4 Non-interactive MFA |

### 12.3 Token Forgery & OAuth 2 Negative Vectors

| Case ID | Scenario / Negative Vector | Injected Input / Payload | Expected Error / Response | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **NEG-14** | Untrusted Private Key Signature | JWT signed with unauthorized rogue RSA/EC private key not in IdP JWKS. | JWT cryptographic signature verification fails; HTTP 401 Unauthorized returned. | OA-2, INT-1 |
| **NEG-15** | Expired JWT Bearer Token | JWT with `exp` timestamp set 10 minutes in the past. | Validation fails with `Token expired`; HTTP 401 returned with `error="invalid_token"`. | RFC 6750 Token Validation |
| **NEG-16** | Untrusted Issuer Claim (`iss`) | JWT with `iss="https://evil-idp.attacker.com"`. | Issuer validation fails against configured trusted issuer; HTTP 401 returned. | OA-1 RFC 8414 Trust Anchor |
| **NEG-17** | Audience Claim Mismatch (`aud`) | JWT with `aud="https://unrelated-service.internal"`. | Audience check rejects token; HTTP 401 returned. | RFC 7519 Audience Protection |
| **NEG-18** | Scope-Stripped JWT Token | Valid JWT containing only `scope="openid email"` (missing `sp:admin`, `sp:operator`). | Token accepted but privilege maps to `none`; any privileged command returns 403 Forbidden. | INT-1 OIDC Scope Mapping |

### 12.4 Dual-Custody Approval Bypass & Tampering

| Case ID | Scenario / Negative Vector | Injected Input / Payload | Expected Error / Response | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **NEG-19** | Self-Approval Exploitation | Administrator who queued `PENDINGCMD_104` attempts to approve their own command. | Dual-custody engine rejects approval: `CANNOT_APPROVE_OWN_COMMAND`. | POL-1 Dual-Custody Invariant |
| **NEG-20** | Approval Token Replay | Caller attempts to re-execute a destructive command using an already consumed approval ID. | Approval state machine marks token `CONSUMED`; subsequent call rejected with `APPROVAL_ALREADY_USED`. | POL-1 Single-Use Approval |
| **NEG-21** | Forged / Non-Existent Approval ID | Calling `approve_pending_command` with random UUID `00000000-0000-0000-0000-000000000000`. | Lookup fails; rejection with `PENDING_COMMAND_NOT_FOUND`; failure recorded in ACTLOG. | POL-1 State Machine Integrity |

### 12.5 Command Injection & Parameter Escaping

| Case ID | Scenario / Negative Vector | Injected Input / Payload | Expected Error / Response | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **NEG-22** | Shell Metacharacter In Node Name | Node name parameter: `NODE01; rm -rf /` or `NODE01 && halt`. | Parameters strictly quoted (`"NODE01; rm -rf /"`); subprocess uses `shell=False`; no shell breakout. | CRED-2 Zero-Trace Execution |
| **NEG-23** | Command Substitution Injection | Volume parameter: `` `id` `` or `$(whoami)`. | Subprocess executed via direct argument vector without shell expansion; literal characters passed. | CRED-2 Zero-Trace Execution |
| **NEG-24** | Newline Sub-Command Splitting | Input parameter containing embedded newlines: `admin_pass\nHALT SERVER`. | Parameter validation rejects embedded newlines; request aborted before CLI dispatch. | Strict Input Sanitization |
| **NEG-25** | SQL Injection in Query Tool | `select_query` input: `SELECT * FROM NODES WHERE 1=1; DROP TABLE ...`. | SP SQL dialect rejects multi-statement execution; read-only service account prevents table modification. | CRED-1 5-Tier Account Separation |

---

## Section 13: Controlled Environmental Failure Test Cases (ENV-01 to ENV-15)

* **Objective**: Evaluate server resilience, automatic error containment, and fail-closed security invariants under injected subprocess crashes, network latency/partitions, IdP outages, and resource starvation.
* **Test Harness**: Containerized test-bed with Toxiproxy chaos proxy and `fault_dsmadmc.py` CLI interceptor as detailed in [`test-bed.md`](test-bed.md).

### 13.1 Subprocess & `dsmadmc` Failure Traps

| Case ID | Failure Scenario | Injected Fault / Trigger | Expected System Behavior | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **ENV-01** | SP Connection Failure (`ANS1017E`) | `fault_dsmadmc.py` injects exit code 8 and stderr `ANS1017E (RC-50) TCP/IP connection failure`. | CLI wrapper catches exit code, formats actionable MCP error envelope; server remains running. | Graceful Subprocess Handling |
| **ENV-02** | Admin Auth Failure (`ANS1025E`) | `fault_dsmadmc.py` injects exit code 12 and stderr `ANS1025E (RC137) Invalid password`. | Increments account failure counter; returns auth error; passwords sanitized from logs. | POL-3 Lockout Policy |
| **ENV-03** | Session Security Mismatch (`ANS1353E`) | `fault_dsmadmc.py` injects exit code 14 and stderr `ANS1353E Session security STRICT required`. | Server detects non-strict security violation; immediately aborts process (`sys.exit(1)`). | NET-1 Fail-Closed Security |
| **ENV-04** | Insufficient SP Privilege (`ANR2017E`) | `fault_dsmadmc.py` injects exit code 4 and stderr `ANR2017E Administrator not authorized`. | Returns MCP privilege error envelope; records non-repudiation event in ACTLOG. | ACC-1 Privilege Boundary |
| **ENV-05** | CLI Subprocess Infinite Hang | `fault_dsmadmc.py` injects `sleep(3600)` blocking stdin/stdout indefinitely. | Subprocess watchdog timer fires after configured timeout (e.g. 30s); sends SIGKILL; returns timeout error. | Watchdog Timeout Enactment |
| **ENV-06** | Subprocess Abnormal Termination | `fault_dsmadmc.py` self-terminates via `SIGKILL` (exit code 137). | Wrapper catches abnormal process death, cleans up file descriptors, releases locks cleanly. | Subprocess Resource Cleanup |

### 13.2 Network Degradation & Partitioning (Toxiproxy)

| Case ID | Failure Scenario | Injected Fault / Trigger | Expected System Behavior | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **ENV-07** | High Latency Spike on SP Port 1500 | Toxiproxy injects 5000ms latency toxic on upstream SP admin port. | Request completes successfully within extended timeout threshold; p95 metrics reflect latency. | Latency Resilience |
| **ENV-08** | Abrupt TCP Reset During SSE Stream | Toxiproxy injects `reset_peer` toxic on active client SSE connection. | Server detects broken pipe (`ECONNRESET`); cleanly terminates SSE generator; frees session memory. | SSE Connection Lifecycle |
| **ENV-09** | Upstream IdP JWKS Endpoint Outage | Toxiproxy injects HTTP 503 Service Unavailable on IdP port 8080. | Server serves existing tokens using cached JWKS; new token validation fails closed with HTTP 401. | OA-3 JWKS Caching Resilience |
| **ENV-10** | Truncated / Corrupt OIDC Discovery Doc | Toxiproxy corrupts JSON payload returned by `/.well-known/openid-configuration`. | Server catches JSON parse error gracefully; falls back to cached configuration or halts securely. | Fail-Closed Discovery |

### 13.3 Storage, Filesystem & Resource Exhaustion

| Case ID | Failure Scenario | Injected Fault / Trigger | Expected System Behavior | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **ENV-11** | ACTLOG Disk Full with Strict Audit | Scratchpad write raises `ENOSPC` with `SP_MCP_STRICT_AUDIT=1`. | Command execution is immediately aborted fail-closed; prevents non-repudiation loss. | NR-2 Strict Audit Invariant |
| **ENV-12** | ACTLOG Disk Full in Standard Audit | Scratchpad write raises `ENOSPC` with `SP_MCP_STRICT_AUDIT=0`. | Server logs warning to stderr, permits command execution, alerts operator of audit degradation. | Degraded Operation Mode |
| **ENV-13** | Insecure Runtime `.env` Permissions | Test script alters `.env` permissions to `0o644` (world-readable) while server runs. | Next credential reload or startup audit detects permission breach; terminates server immediately. | CRED-3 POSIX 0600 File Guard |
| **ENV-14** | Temporary Scratch Space Exhaustion | Scratch directory `/tmp` filled to 100% capacity (`ENOSPC`). | Streamed output avoids disk-buffering; command returns resource error without unhandled trace. | Resource Starvation Defense |
| **ENV-15** | File Descriptor Exhaustion | Server process file descriptor limit artificially set to 32 FDs. | Server gracefully throttles incoming requests, returns HTTP 503, avoids socket leak panic. | Bounded Descriptor Hygiene |

---

## Section 14: Stress, Capacity & Load Test Cases (STR-01 to STR-10)

* **Objective**: Measure throughput, connection concurrency, memory stability, and rate-limiting enforcement under sustained and peak synthetic workloads.
* **Test Harness**: Locust distributed load generator and AnyIO worker pools executing against the test-bed topology.

| Case ID | Test Method / Scenario | Concurrency & Workload Profile | Target Metrics / Pass Criteria | Invariant Enforced |
| :--- | :--- | :--- | :--- | :--- |
| **STR-01** | Sustained 100 Concurrent AI Agent Sessions | 100 concurrent workers issuing `query_status`, `query_session`, `query_volume` over 10 minutes. | Zero HTTP 5xx errors; p95 latency < 500ms (excluding backend mock); 100% request completion. | Throughput & Stability |
| **STR-02** | 200 Concurrent Dynamic Auth Handshakes | 200 concurrent clients executing `authenticate` -> `execute` -> `delete_session` in parallel. | Zero deadlocks; `SessionManager` locks cleanly; zero credential collisions; all sessions cleaned. | DAUTH-1 Concurrency Safety |
| **STR-03** | 10,000 Ephemeral Session Churn | Rapid creation and retirement of 10,000 short-lived sessions (TTL=10s) over 15 minutes. | Expired sessions pruned automatically; heap memory RSS remains bounded <= 256MB; zero leaks. | DAUTH-4 Bounded Memory |
| **STR-04** | JWKS Cache Stampede Under Burst Traffic | Burst of 500 concurrent requests each bearing an unassigned Key ID (`kid`). | Rate limiter caps outbound IdP JWKS requests to max 5 req/sec; prevents upstream IdP throttling. | OA-3 Rate-Limit Throttling |
| **STR-05** | High-Volume ACTLOG Streaming (100k Records) | Query generating 100,000 ACTLOG records streamed over SSE. | Stream generator yields rows in 1,000-record chunks; server memory RSS remains flat; zero buffering panic. | Streaming Scalability |
| **STR-06** | Slow-Consumer SSE Stream Backpressure | Client SSE socket artificially throttled to 10 bytes/sec on high-frequency log stream. | Server ASGI buffer does not overflow; bounded queue drops/slows smoothly; disconnect triggers cleanup. | Socket Buffer Backpressure |
| **STR-07** | Large Payload Stress (100MB Node Dataset) | Mock backend returns 100MB JSON payload from `query_occupancy`. | Streaming JSON parser parses and formats payload without triggering Python MemoryError. | Large Payload Integrity |
| **STR-08** | Rapid Execution Context Reset Cycling | 1,000 concurrent asyncio tasks repeatedly calling `reset_execution_state()` and setting ContextVars. | Zero cross-task context leakage; ContextVar values stay isolated per execution frame. | AUD-F-01 Isolation Guard |
| **STR-09** | High-Frequency Brute-Force Password Lockout | 100 failed login attempts within 5 seconds targeting a single admin account. | Account locked after 3rd failure (`INVALIDPWLIMIT=3`); remaining 97 attempts rejected immediately without SP backend calls. | POL-3 Lockout Invariant |
| **STR-10** | 24-Hour Continuous Soak / Endurance Test | 10 requests/sec steady workload sustained over 24 hours in containerized test-bed. | Memory RSS delta <= 5% over 24h; zero orphan subprocesses; zero leaked socket descriptors. | Long-Term Reliability |

