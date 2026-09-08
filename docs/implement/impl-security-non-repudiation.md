# Implementation: Non-Repudiation & Forensic Auditability

* **Domain**: Non-Repudiation & Forensic Auditability
* **Analysis reference**: [`docs/analysis/security-design-analysis.md § 7`](../analysis/security-design-analysis.md)
* **Design reference**: [`docs/design/security-non-repudiation.md`](../design/security-non-repudiation.md)
* **Gaps addressed**: NR-1, NR-2, NR-3, NR-4, NR-5
* **Files changed**: `src/sp_mcp_server/mcp_factory.py`, `src/sp_mcp_server/http_server.py`, `tests/test_security_controls.py`

---

## 1. Overview

This document provides the implementation specifications and runbooks for achieving high-assurance non-repudiation and forensic traceability within the IBM Storage Protect MCP Server.

---

## 2. Implemented Code Changes

### 2.1 NR-1: Identity Context Propagation & Enriched Scratchpad Payload

In `src/sp_mcp_server/mcp_factory.py`, a `contextvars.ContextVar` captures the active user/subject:
```python
current_audit_user: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("current_audit_user", default=None)
```

In `src/sp_mcp_server/http_server.py`, the `OIDCBearerMiddleware` sets this context variable for the duration of the request:
```python
from .mcp_factory import current_audit_user
token_ctx = current_audit_user.set(scope["state"]["mcp_subject"])
try:
    await self.app(scope, receive, send)
finally:
    current_audit_user.reset(token_ctx)
```

In `handle_call_tool()`, the audit payload binds the user identity into the `DEFINE SCRATCHPADENTRY` message:
```python
user_id = current_audit_user.get() or os.environ.get("SP_MCP_USER") or "local"
audit_msg = (
    f"MCP_AUDIT user={user_id} "
    f"tool={name} "
    f"priv={tool_privilege} "
    f"corr={correlation_id}"
)
```

### 2.2 NR-4: Strict Fail-Closed Audit Mode

When `SP_MCP_STRICT_AUDIT=1` is set in the server environment, `handle_call_tool()` blocks execution if the SP ACTLOG scratchpad write fails:
```python
strict_audit = os.environ.get("SP_MCP_STRICT_AUDIT", "0") == "1"
if _code != 0:
    logger.error("SECURITY [POL-4 / RG-4 / NR-4]: Audit write FAILED...")
    if strict_audit:
        raise RuntimeError(f"Strict audit failure: unable to record ACTLOG entry ({_stderr})")
```

### 2.3 NR-5: ISO 8601 UTC Timestamp Formatting

In `setup_logging()` in `src/sp_mcp_server/mcp_factory.py`, formatters enforce UTC standard timestamps:
```python
detailed_formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%dT%H:%M:%SZ'
)
detailed_formatter.converter = time.gmtime
```

---

## 3. Storage Protect Host Hardening & Forensic Retention

### 3.1 Retain Scratchpad and Activity Logs (NR-2, NR-3)
On the IBM Storage Protect Server, configure adequate audit retention windows (minimum 90 days for compliance):
```
* Set scratchpad entry retention to 90 days
SET SCRATCHPADRETENTION 90

* Set Activity Log retention to 90 days
SET ACTLOGRETENTION 90

* Enable logging receivers for file and console
ENABLE EVENTS FILE ALL
ENABLE EVENTS CONSOLE ALL
```

### 3.2 Protecting Log Files on Host (NR-2)
Ensure `/var/log/ibm-sp-mcp-server` has restricted access and optionally set append-only file attributes on Linux:
```bash
chmod 700 /var/log/ibm-sp-mcp-server
chown -R mcp-runner:mcp-runner /var/log/ibm-sp-mcp-server

# Optional: set append-only attribute to prevent tampering (requires root)
chattr +a /var/log/ibm-sp-mcp-server/mcp-server.log
```

---

## 4. Verification & Testing

Verify non-repudiation and audit controls:
```bash
# Run security test suite including NR-1, NR-4, NR-5
.venv/bin/pytest tests/test_security_controls.py -k "TestAuditTrail"
```
