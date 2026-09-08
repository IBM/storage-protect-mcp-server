#!/usr/bin/env bash
# scripts/provision-sp-service-accounts.sh
#
# Provisions five MCP service accounts on an IBM Storage Protect server.
# Each account is scoped to the narrowest SP privilege class needed by the
# corresponding MCP server module (system / policy / storage / operator / read-only).
#
# Usage:
#   export SP_ADMIN_ID=<your-system-privileged-admin>
#   export SP_ADMIN_PASSWORD=<password>
#   export MCP_PWD_READONLY=$(openssl rand -base64 20)
#   export MCP_PWD_OPERATOR=$(openssl rand -base64 20)
#   export MCP_PWD_STORAGE=$(openssl rand -base64 20)
#   export MCP_PWD_POLICY=$(openssl rand -base64 20)
#   export MCP_PWD_SYSTEM=$(openssl rand -base64 20)
#   # Store the generated passwords securely, then:
#   bash scripts/provision-sp-service-accounts.sh
#
# Prerequisites:
#   - dsmadmc in PATH, or DSM_CONFIG pointing at the correct dsm.sys.
#   - A system-privileged SP admin (SP_ADMIN_ID / SP_ADMIN_PASSWORD).
#   - IBM SP v8.1.16+ (MINPWLENGTH defaults to 15).
#
# Idempotency:
#   If an account already exists, REGISTER ADMIN returns ANR2074E which is
#   suppressed; UPDATE ADMIN is always re-applied to enforce the policy.
#
# References:
#   - docs/implement/impl-security-identity-credentials.md § CRED-5
#   - docs/analysis/security-design-analysis.md § 2 (gaps I1, I4, I5)
#
set -euo pipefail

# ── Required variables ─────────────────────────────────────────────────────────
: "${SP_ADMIN_ID:?SP_ADMIN_ID must be set to a system-privileged SP admin}"
: "${SP_ADMIN_PASSWORD:?SP_ADMIN_PASSWORD must be set}"
: "${MCP_PWD_READONLY:?MCP_PWD_READONLY must be set (use: openssl rand -base64 20)}"
: "${MCP_PWD_OPERATOR:?MCP_PWD_OPERATOR must be set}"
: "${MCP_PWD_STORAGE:?MCP_PWD_STORAGE must be set}"
: "${MCP_PWD_POLICY:?MCP_PWD_POLICY must be set}"
: "${MCP_PWD_SYSTEM:?MCP_PWD_SYSTEM must be set}"

DSMADMC_BASE="-NOConfirm -DATAONLY=YES"

# ── Helper: run a dsmadmc command, tolerating "already exists" errors ──────────
run_sp() {
    local cmd="$*"
    local output rc
    output=$(dsmadmc $DSMADMC_BASE \
        -id="${SP_ADMIN_ID}" -pa="${SP_ADMIN_PASSWORD}" \
        "${cmd}" 2>&1) && rc=0 || rc=$?

    # ANR2074E = Admin already defined — safe to ignore for REGISTER ADMIN
    if echo "${output}" | grep -q "ANR2074E"; then
        echo "  [INFO] Account already exists — UPDATE ADMIN will be applied."
        rc=0
    fi

    if [[ $rc -ne 0 ]]; then
        echo "  [ERROR] dsmadmc returned $rc for: ${cmd}"
        echo "  [ERROR] Output: ${output}"
        exit $rc
    fi

    echo "${output}"
}

echo "==================================================================="
echo " IBM Storage Protect — MCP Service Account Provisioning"
echo " Server: ${TCPSERVERADDRESS:-<default from dsm.sys>}"
echo "==================================================================="

# ── 1. Read-only (any-admin, no privilege class) ───────────────────────────────
echo ""
echo "--- Provisioning mcp-svc-readonly (any-admin / read-only) ---"
run_sp "REGISTER ADMIN mcp-svc-readonly ${MCP_PWD_READONLY} \
    CONTACT='MCP read-only service account'"
run_sp "UPDATE ADMIN mcp-svc-readonly \
    SESSIONSECURITY=STRICT \
    PASSWORDEXPIRATION=30 \
    MFAREQUIRED=NO"

# ── 2. Operator ────────────────────────────────────────────────────────────────
echo ""
echo "--- Provisioning mcp-svc-operator (Operator privilege class) ---"
run_sp "REGISTER ADMIN mcp-svc-operator ${MCP_PWD_OPERATOR} \
    CONTACT='MCP operator service account'"
run_sp "GRANT AUTHORITY mcp-svc-operator CLASSES=OPERATOR"
run_sp "UPDATE ADMIN mcp-svc-operator \
    SESSIONSECURITY=STRICT \
    PASSWORDEXPIRATION=30 \
    MFAREQUIRED=NO"

# ── 3. Storage ─────────────────────────────────────────────────────────────────
echo ""
echo "--- Provisioning mcp-svc-storage (Storage privilege class) ---"
run_sp "REGISTER ADMIN mcp-svc-storage ${MCP_PWD_STORAGE} \
    CONTACT='MCP storage service account'"
run_sp "GRANT AUTHORITY mcp-svc-storage CLASSES=STORAGE"
run_sp "UPDATE ADMIN mcp-svc-storage \
    SESSIONSECURITY=STRICT \
    PASSWORDEXPIRATION=30 \
    MFAREQUIRED=NO"

# ── 4. Policy ──────────────────────────────────────────────────────────────────
echo ""
echo "--- Provisioning mcp-svc-policy (Policy privilege class) ---"
run_sp "REGISTER ADMIN mcp-svc-policy ${MCP_PWD_POLICY} \
    CONTACT='MCP policy service account'"
run_sp "GRANT AUTHORITY mcp-svc-policy CLASSES=POLICY"
run_sp "UPDATE ADMIN mcp-svc-policy \
    SESSIONSECURITY=STRICT \
    PASSWORDEXPIRATION=30 \
    MFAREQUIRED=NO"

# ── 5. System ──────────────────────────────────────────────────────────────────
echo ""
echo "--- Provisioning mcp-svc-system (System privilege class) ---"
run_sp "REGISTER ADMIN mcp-svc-system ${MCP_PWD_SYSTEM} \
    CONTACT='MCP system service account'"
run_sp "GRANT AUTHORITY mcp-svc-system CLASSES=SYSTEM"
run_sp "UPDATE ADMIN mcp-svc-system \
    SESSIONSECURITY=STRICT \
    PASSWORDEXPIRATION=30 \
    MFAREQUIRED=NO"

# ── Verification ───────────────────────────────────────────────────────────────
echo ""
echo "--- Verification: QUERY ADMIN mcp-svc-* FORMAT=DETAILED ---"
dsmadmc $DSMADMC_BASE \
    -id="${SP_ADMIN_ID}" -pa="${SP_ADMIN_PASSWORD}" \
    "QUERY ADMIN mcp-svc-* FORMAT=DETAILED" \
    | grep -E "(Admin Name|System Priv|Storage Priv|Policy Priv|Operator Priv|Session Security|MFAR|Password Expir)" \
    || true

echo ""
echo "==================================================================="
echo " Done. Run this script on each SP server instance."
echo " Next step: populate dsm.sys stash (see configure-guide.md)."
echo " Then set SP_MCP_USE_PASSWORD_STASH=1 in your .env file."
echo "==================================================================="
