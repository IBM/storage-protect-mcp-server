#!/usr/bin/env bash
# scripts/provision-sp-service-accounts.sh
#
# Provisions five MCP service accounts on the IBM SP server.
#
# Usage:
#   export SP_ADMIN_ID=<your-system-admin>
#   export SP_ADMIN_PASSWORD=<your-system-admin-password>
#   export MCP_PWD_READONLY=$(openssl rand -base64 20)
#   export MCP_PWD_OPERATOR=$(openssl rand -base64 20)
#   export MCP_PWD_STORAGE=$(openssl rand -base64 20)
#   export MCP_PWD_POLICY=$(openssl rand -base64 20)
#   export MCP_PWD_SYSTEM=$(openssl rand -base64 20)
#   bash scripts/provision-sp-service-accounts.sh
#
# The script is idempotent — accounts that already exist receive
# UPDATE ADMIN instead of REGISTER ADMIN.
#
# Prerequisites:
#   - A system-privileged SP admin (SP_ADMIN_ID / SP_ADMIN_PASSWORD).
#   - IBM SP v8.1.16+ (MINPWLENGTH defaults to 15; passwords generated
#     by openssl rand -base64 20 satisfy this requirement).
#   - dsmadmc in PATH and DSM_CONFIG pointing at a valid dsm.sys.
#
# See: docs/implement/impl-security-identity-credentials.md § CRED-5
#      docs/guides/install-guide.md § Part 5

set -euo pipefail

: "${SP_ADMIN_ID:?SP_ADMIN_ID must be set}"
: "${SP_ADMIN_PASSWORD:?SP_ADMIN_PASSWORD must be set}"
: "${MCP_PWD_READONLY:?MCP_PWD_READONLY must be set}"
: "${MCP_PWD_OPERATOR:?MCP_PWD_OPERATOR must be set}"
: "${MCP_PWD_STORAGE:?MCP_PWD_STORAGE must be set}"
: "${MCP_PWD_POLICY:?MCP_PWD_POLICY must be set}"
: "${MCP_PWD_SYSTEM:?MCP_PWD_SYSTEM must be set}"

DSMADMC_OPTS="-NOConfirm -DATAONLY=YES"

run_sp() {
    dsmadmc $DSMADMC_OPTS -id="${SP_ADMIN_ID}" -pa="${SP_ADMIN_PASSWORD}" "$@"
}

echo "=== Provisioning MCP service accounts on SP server ==="

# ── Read-only (any-admin, no privilege class) ──────────────────────────
run_sp "REGISTER ADMIN mcp-svc-readonly ${MCP_PWD_READONLY} CONTACT='MCP readonly service account'"
run_sp "UPDATE ADMIN mcp-svc-readonly SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── Operator ───────────────────────────────────────────────────────────
run_sp "REGISTER ADMIN mcp-svc-operator ${MCP_PWD_OPERATOR} CONTACT='MCP operator service account'"
run_sp "GRANT AUTHORITY mcp-svc-operator CLASSES=OPERATOR"
run_sp "UPDATE ADMIN mcp-svc-operator SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── Storage ────────────────────────────────────────────────────────────
run_sp "REGISTER ADMIN mcp-svc-storage ${MCP_PWD_STORAGE} CONTACT='MCP storage service account'"
run_sp "GRANT AUTHORITY mcp-svc-storage CLASSES=STORAGE"
run_sp "UPDATE ADMIN mcp-svc-storage SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── Policy ─────────────────────────────────────────────────────────────
run_sp "REGISTER ADMIN mcp-svc-policy ${MCP_PWD_POLICY} CONTACT='MCP policy service account'"
run_sp "GRANT AUTHORITY mcp-svc-policy CLASSES=POLICY"
run_sp "UPDATE ADMIN mcp-svc-policy SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── System ─────────────────────────────────────────────────────────────
run_sp "REGISTER ADMIN mcp-svc-system ${MCP_PWD_SYSTEM} CONTACT='MCP system service account'"
run_sp "GRANT AUTHORITY mcp-svc-system CLASSES=SYSTEM"
run_sp "UPDATE ADMIN mcp-svc-system SESSIONSECURITY=STRICT PASSWORDEXPIRATION=30 MFAREQUIRED=NO"

# ── Verify ─────────────────────────────────────────────────────────────
echo "=== Verifying accounts ==="
run_sp "QUERY ADMIN mcp-svc-* FORMAT=DETAILED" \
    | grep -E "(Admin Name|System Priv|Storage Priv|Policy Priv|Operator Priv|Session Security|MFAR)"

echo "=== Done. Run this script on each SP server that MCP manages. ==="
