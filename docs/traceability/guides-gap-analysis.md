# IBM Storage Protect MCP Server — Guides Gap Analysis

* **Revision**: 2026-10
* **Scope**: Consistency, correctness, and completeness of `docs/guides/` against `docs/design/`, `docs/implement/`, and `src/sp_mcp_server/`
* **Method**: Static cross-reference of all guide content against design specifications, implementation specs, and source files (`main.py`, `http_server.py`, `config.py`, `mcp_factory.py`)
* **Cross-reference**: [`docs/traceability/audit-report.md`](audit-report.md) · [`docs/traceability/gap-analysis.md`](gap-analysis.md) · [`docs/traceability/traceability-matrix.md`](traceability-matrix.md)

---

## 1. Executive Summary

The guides are **substantially consistent and correct**. All critical security controls, environment variable names, command syntax, and architectural descriptions match the implementation. Five issues were identified: two factual/functional errors, two omissions, and one structural bug. No guide contains misinformation that would cause a security breach or broken deployment; the issues are documentation accuracy and completeness problems.

---

## 2. Overall Posture by Guide

| Guide | Status | Issues |
| :--- | :---: | :--- |
| [`planning-guide.md`](../guides/planning-guide.md) | ✅ Fixed | Duplicate "Step 4" heading corrected — Steps 5–10 renumbered (GGA-04) |
| [`install-guide.md`](../guides/install-guide.md) | ✅ Fixed | 6 OA-era HTTP transport env vars added to reference table (GGA-02) |
| [`configure-guide.md`](../guides/configure-guide.md) | ✅ Fixed | Introspection keyring snippet replaced with correct `.env` instruction (GGA-05) |
| [`user-guide.md`](../guides/user-guide.md) | ✅ Correct | No issues found |
| [`local-idp-oauth2-guide.md`](../guides/local-idp-oauth2-guide.md) | ✅ Correct | No issues found |
| [`troubleshoot.md`](../guides/troubleshoot.md) | ✅ Correct | No issues found |

---

## 3. Findings

### GGA-01 — Env Var Defaults: No Discrepancy ✅

**Scope**: All guides referencing `SP_OIDC_JWKS_TTL`, `SP_OIDC_INTROSPECT_BELOW_TTL`, `SP_OIDC_AUDIENCE`, and `SP_MCP_SESSION_TTL` defaults.

**Finding**: All default values in the guides match the source:

| Variable | Source default | Guide value |
| :--- | :---: | :---: |
| `SP_OIDC_JWKS_TTL` | `3600` (`main.py:122`) | `3600` ✅ |
| `SP_OIDC_INTROSPECT_BELOW_TTL` | `300` (`main.py:127`) | `300` ✅ |
| `SP_OIDC_AUDIENCE` | `sp-mcp-server` (`main.py:106`) | `sp-mcp-server` ✅ |
| `SP_MCP_SESSION_TTL` | `900` | `900` ✅ |
| `SP_MCP_SESSION_MAX_TTL` | `3600` | `3600` ✅ |

**Status**: ✅ No action required.

---

### GGA-02 — `install-guide.md`: OA-Era HTTP Variables Missing from Env Var Reference ⚠️

**File**: [`docs/guides/install-guide.md` §Complete environment variable reference](../guides/install-guide.md)

**Finding**: The install guide's complete environment variable reference table and the full `.env` template (Part 4) include only the four baseline HTTP transport variables from the INT-2 era. The six OA-era variables added in revision 2026-10 are absent.

**Missing variables** (all present in `main.py` and fully documented in `configure-guide.md`):

| Variable | Source | Implemented by |
| :--- | :--- | :--- |
| `SP_OIDC_JWKS_TTL` | `main.py:122` | OA-2 |
| `SP_MCP_PUBLIC_URL` | `main.py:123` | OA-6 |
| `SP_OIDC_INTROSPECTION_ENDPOINT` | `main.py:124` | OA-5 |
| `SP_OIDC_INTROSPECTION_CLIENT_ID` | `main.py:125` | OA-5 |
| `SP_OIDC_INTROSPECTION_CLIENT_SECRET` | `main.py:126` | OA-5 |
| `SP_OIDC_INTROSPECT_BELOW_TTL` | `main.py:127` | OA-5 / OA-6 |

**Impact**: Operators following only the install guide as a reference will not know these variables exist. The `configure-guide.md` Part 2 complete reference table is correct and complete — but the install guide is the canonical "what env vars does this server accept" reference for many operators.

**Remediation**: Add the six missing variables to the `install-guide.md` complete env var reference table under the existing HTTP transport section, with a note pointing to `configure-guide.md` Part 2 for full descriptions.

**Status**: ✅ Closed — 6 rows added to the `install-guide.md` env var reference table with a pointer to `configure-guide.md` Part 2 for full descriptions.

---

### GGA-03 — Startup Log Format Discrepancy: No Factual Error ✅

**Files**: [`install-guide.md` Part 8](../guides/install-guide.md) and [`configure-guide.md` §Starting the HTTP transport](../guides/configure-guide.md)

**Finding**: The `install-guide.md` Part 8 dry-run uses stdio transport (no `--transport http`) and does not claim the `OA-1` / `OA-4` / `RG-5` log lines appear. The `configure-guide.md` shows those lines only in the HTTP transport startup section. There is no inconsistency — the two guides describe different startup paths. No factual error.

**Status**: ✅ No action required.

---

### GGA-04 — `planning-guide.md`: Duplicate "Step 4" Heading ⚠️

**File**: [`docs/guides/planning-guide.md`](../guides/planning-guide.md)

**Finding**: Both the table of contents and the document body contain two sections numbered **"Step 4"**:

- `## Step 4 — Prerequisites Checklist` (correct — appears after Step 3)
- `## Step 4 — Plan Your Service Accounts` (should be **Step 5**; current Steps 5–9 should be renumbered 6–10)

This produces a broken sequential flow. Operators following the numbered steps will reach "Step 4" twice and may mis-track their progress.

**Affected headings requiring renumbering**:

| Current heading | Correct heading |
| :--- | :--- |
| `## Step 4 — Plan Your Service Accounts` | `## Step 5 — Plan Your Service Accounts` |
| `## Step 5 — Plan Your dsm.sys SERVERNAME Labels` | `## Step 6 — Plan Your dsm.sys SERVERNAME Labels` |
| `## Step 6 — Plan Your SSH Keys` | `## Step 7 — Plan Your SSH Keys` |
| `## Step 7 — Plan Your MCP Client Configuration Entry Names` | `## Step 8 — Plan Your MCP Client Configuration Entry Names` |
| `## Step 8 — Plan Your Tool Scope per SP Server` | `## Step 9 — Plan Your Tool Scope per SP Server` |
| `## Step 9 — Pre-Installation Sign-off` | `## Step 10 — Pre-Installation Sign-off` |

The table of contents, anchor links, and any cross-references using step numbers also need updating.

**Status**: ✅ Closed — ToC updated and body headings renumbered: Steps 5–10 in `planning-guide.md`.

---

### GGA-05 — `configure-guide.md`: Introspection Keyring Snippet Is Dead Code ❌

**File**: [`docs/guides/configure-guide.md` §Token introspection / revocation](../guides/configure-guide.md)

**Finding**: The guide instructs operators to store the introspection client secret in the OS keyring:

```python
keyring.set_password(
    "ibm-sp-mcp-server",
    "introspection-secret",
    getpass.getpass("Introspection client secret: ")
)
```

**Source reality** (`main.py:126`):
```python
introspection_client_secret = os.environ.get("SP_OIDC_INTROSPECTION_CLIENT_SECRET")
```

`SP_OIDC_INTROSPECTION_CLIENT_SECRET` is read **only** from `os.environ`. The `_get_password()` / keyring resolution in `config.py` is used exclusively for SP service account passwords (keyed by admin ID under `"ibm-sp-mcp-server"`). Nothing in the codebase calls `keyring.get_password("ibm-sp-mcp-server", "introspection-secret")`. The guide's `keyring.set_password(...)` snippet stores a value that is never retrieved.

**Impact**: Operators who follow the guide, store the secret in keyring, and omit it from their environment will find introspection silently skipped (the `OIDCBearerMiddleware._introspect()` guard at line 266 returns `True` when `introspection_client_secret` is falsy, logging a warning). This is a security control gap: token introspection will not function even though the operator believes they have configured it correctly.

**Remediation options** (two paths — choose one):

**Option A — Fix the guide (documentation only):** Replace the keyring snippet with the correct instruction: set `SP_OIDC_INTROSPECTION_CLIENT_SECRET` in the `.env` file (with `chmod 600`) or in the process environment, and explicitly note that keyring resolution is not currently implemented for this variable:

```dotenv
# Store in .env (permissions 600) or inject via systemd EnvironmentFile / Vault agent
SP_OIDC_INTROSPECTION_CLIENT_SECRET=<secret>
```

**Option B — Fix the implementation (source change):** Extend `main.py` to resolve `SP_OIDC_INTROSPECTION_CLIENT_SECRET` through `_get_password()` using a fixed keyring key (e.g., `"sp-mcp-introspection-secret"`), making the guide's intent correct:

```python
# main.py — after reading introspection_client_id
introspection_client_secret = _get_password(
    "sp-mcp-introspection-secret", "SP_OIDC_INTROSPECTION_CLIENT_SECRET"
)
```

Option B aligns with the INT-4 keyring-first design principle and is the more complete fix. Option A is the minimal documentation-only correction.

**Status**: ✅ Closed — keyring snippet replaced with correct `.env` instruction; env var reference table updated from `keyring` → `unset`; note added explaining keyring is not implemented for this variable and documenting the wrapper-script workaround for operators who want keyring storage.

---

## 4. Summary Table

| ID | Severity | File | Finding | Status |
| :--- | :---: | :--- | :--- | :---: |
| GGA-01 | ✅ None | Multiple | All env var defaults match source | Closed |
| GGA-02 | ⚠️ Omission | `install-guide.md` | 6 OA-era HTTP vars absent from env var reference table | ✅ Fixed |
| GGA-03 | ✅ None | `install-guide.md` / `configure-guide.md` | Startup log format difference is intentional (different transports) | Closed |
| GGA-04 | ⚠️ Structural | `planning-guide.md` | Duplicate "Step 4" heading; Steps 5–9 mis-numbered | ✅ Fixed |
| GGA-05 | ❌ Functional | `configure-guide.md` | Introspection keyring snippet stores value the code never reads; introspection silently skipped | ✅ Fixed |

**Open findings**: 0
**Closed / fixed**: 5 (GGA-01 through GGA-05)

---

## 5. Remediation Record

| Priority | Finding | Resolution | Files changed |
| :---: | :--- | :--- | :--- |
| 1 (High) | **GGA-05** — Introspection credential resolution gap | Replaced dead keyring snippet with `.env` instruction; added note on keyring limitation and wrapper workaround; fixed reference table default value | `configure-guide.md` |
| 2 (Medium) | **GGA-02** — Missing OA-era vars from install-guide reference table | Added 6 rows (`SP_MCP_PUBLIC_URL`, `SP_OIDC_JWKS_TTL`, `SP_OIDC_INTROSPECTION_ENDPOINT`, `SP_OIDC_INTROSPECTION_CLIENT_ID`, `SP_OIDC_INTROSPECTION_CLIENT_SECRET`, `SP_OIDC_INTROSPECT_BELOW_TTL`) plus cross-reference note | `install-guide.md` |
| 3 (Low) | **GGA-04** — Duplicate Step 4 in planning-guide | Renumbered ToC and body headings: Plan Service Accounts→5, SERVERNAME→6, SSH Keys→7, Entry Names→8, Tool Scope→9, Sign-off→10 | `planning-guide.md` |

---

## 6. Verified Correct Areas

The following guide content was cross-checked against design docs and source and found **correct and complete**:

- All scope → privilege mappings (`configure-guide.md` Part 2, `user-guide.md`) match `SCOPE_PRIVILEGE_MAP` in `http_server.py:34`
- All privilege tier names and their tool scopes match `PRIVILEGE_TIERS` in `config.py:21` and `_PRIVILEGE_SATISFIES` in `mcp_factory.py`
- OA-1 route path `/.well-known/oauth-authorization-server` and OA-6 route `/.well-known/oauth-protected-resource` match `create_http_app()` route registration in `http_server.py:464–466`
- `authmodel` labels (`client_credentials`, `oidc_bearer`, `dynamic_session`, `local`) match detection logic in `http_server.py:377–382` and `mcp_factory.py`
- ACTLOG record format (`MCP_AUDIT user=… authmodel=… tool=… priv=… corr=…`) matches `handle_call_tool()` audit string construction
- `SP_MCP_ALLOW_HTTP_PLAINTEXT=1` behaviour (logs `ERROR`, continues) matches `main.py:146–151`
- Dynamic auth flow, session TTL env vars, and `AUTHENTICATION_REQUIRED` response format match `session.py` and `mcp_factory.py`
- `SP_MCP_USE_PASSWORD_STASH=1` omitting `-PA=` matches `cli_wrapper.py DsmAdmcWrapper.execute()`
- `CRED-3` permission check abort behaviour matches `config.py:check_env_file_permissions()`
- `RG-1` production guard (`SP_MCP_ENV=production` blocking `SP_MCP_SKIP_SECURITY_CHECKS=1`) matches `mcp_factory.py:115–120`
- `dsm.sys` template fields (`SSL Yes`, `SSLREQUIRED Yes`, `PASSWORDACCESS GENERATE`) match `config/dsm.sys.template`
- Keyring resolution for service account passwords (`keyring.set_password("ibm-sp-mcp-server", "<admin-id>", ...)`) correctly matches `_get_password()` in `config.py:142–145`
- `troubleshoot.md` error markers all match actual log strings in source

---

## 7. Related Documents

- Security audit: [`audit-report.md`](audit-report.md)
- Requirements traceability: [`traceability-matrix.md`](traceability-matrix.md)
- Security gap analysis: [`gap-analysis.md`](gap-analysis.md)
- Design specifications: [`../design/`](../design/)
- Implementation specifications: [`../implement/`](../implement/)
- Guides: [`../guides/`](../guides/)
