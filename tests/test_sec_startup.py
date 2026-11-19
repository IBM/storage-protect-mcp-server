"""
Security-control regression tests — startup & privilege filtering.

Controls covered:
  NET-1  _validate_session_security() rejects non-STRICT accounts
  RG-1   SP_MCP_SKIP_SECURITY_CHECKS blocked when SP_MCP_ENV=production
  CRED-3 check_env_file_permissions() rejects world/group-readable .env
  RG-2   secure_startup() combines permission check + dotenv atomically
  ACC-2  tool list filtered to privilege-appropriate subset
  POL-3  _check_lockout_policy() warns when INVALIDPWLIMIT=0
"""

import logging
import os
import pytest

from sp_mcp_server.config import (
    check_env_file_permissions,
    secure_startup,
)
from sp_mcp_server.mcp_factory import (
    _validate_session_security,
    _check_lockout_policy,
)

from tests.fixtures import (
    make_config_with_cred,
    mock_admc,
    SVC_ADMIN_ID,
    SVC_ADMIN_PASSWORD,
    SP_OUTPUT_SESSION_STRICT_TLS12,
    SP_OUTPUT_SESSION_STRICT_ONLY,
    SP_OUTPUT_SESSION_TRANSITIONAL,
    SP_OUTPUT_PRIVILEGE_SYSTEM,
    SP_OUTPUT_PRIVILEGE_OPERATOR,
    SP_OUTPUT_PRIVILEGE_NONE,
    SP_OUTPUT_LOCKOUT_ZERO,
    SP_OUTPUT_LOCKOUT_FIVE,
    SP_OUTPUT_CONN_REFUSED_STDERR,
    SP_OUTPUT_CONN_FAILED_STDERR,
)


def _cfg(admin_id=SVC_ADMIN_ID, password=SVC_ADMIN_PASSWORD):
    return make_config_with_cred(admin_id=admin_id, password=password)


# ─────────────────────────────────────────────────────────────────────────────
# NET-1: _validate_session_security
# ─────────────────────────────────────────────────────────────────────────────

class TestValidateSessionSecurity:
    """NET-1 — startup session-security validation."""

    def test_exits_when_session_security_not_strict(self, monkeypatch):
        monkeypatch.delenv("SP_MCP_SKIP_SECURITY_CHECKS", raising=False)
        admc = mock_admc(stdout=SP_OUTPUT_SESSION_TRANSITIONAL, code=0)
        with pytest.raises(SystemExit) as exc:
            _validate_session_security(admc, _cfg())
        assert exc.value.code == 1

    def test_exits_when_query_fails(self, monkeypatch):
        monkeypatch.delenv("SP_MCP_SKIP_SECURITY_CHECKS", raising=False)
        admc = mock_admc(stdout="", stderr=SP_OUTPUT_CONN_REFUSED_STDERR, code=1)
        with pytest.raises(SystemExit) as exc:
            _validate_session_security(admc, _cfg())
        assert exc.value.code == 1

    def test_passes_when_strict_and_tls(self, monkeypatch):
        monkeypatch.delenv("SP_MCP_SKIP_SECURITY_CHECKS", raising=False)
        admc = mock_admc(stdout=SP_OUTPUT_SESSION_STRICT_TLS12, code=0)
        _validate_session_security(admc, _cfg())  # must not raise

    def test_passes_when_strict_and_blank_transport(self, monkeypatch):
        """Blank Transport Method is accepted — older SP versions don't report it."""
        monkeypatch.delenv("SP_MCP_SKIP_SECURITY_CHECKS", raising=False)
        admc = mock_admc(stdout=SP_OUTPUT_SESSION_STRICT_ONLY, code=0)
        _validate_session_security(admc, _cfg())  # must not raise

    def test_skip_flag_bypasses_check_non_production(self, monkeypatch):
        """SP_MCP_SKIP_SECURITY_CHECKS=1 without SP_MCP_ENV=production skips check."""
        monkeypatch.setenv("SP_MCP_SKIP_SECURITY_CHECKS", "1")
        monkeypatch.delenv("SP_MCP_ENV", raising=False)
        admc = mock_admc(stdout="", code=1)  # would fail if check ran
        _validate_session_security(admc, _cfg())  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# RG-1: production guard for SP_MCP_SKIP_SECURITY_CHECKS
# ─────────────────────────────────────────────────────────────────────────────

class TestProductionGuard:
    """RG-1 — SP_MCP_SKIP_SECURITY_CHECKS blocked in production."""

    def test_exits_when_skip_set_in_production(self, monkeypatch):
        monkeypatch.setenv("SP_MCP_SKIP_SECURITY_CHECKS", "1")
        monkeypatch.setenv("SP_MCP_ENV", "production")
        admc = mock_admc()
        with pytest.raises(SystemExit) as exc:
            _validate_session_security(admc, _cfg())
        assert exc.value.code == 1

    def test_allows_skip_in_non_production(self, monkeypatch):
        monkeypatch.setenv("SP_MCP_SKIP_SECURITY_CHECKS", "1")
        monkeypatch.setenv("SP_MCP_ENV", "test")
        admc = mock_admc()
        _validate_session_security(admc, _cfg())  # must not raise

    def test_allows_skip_with_no_env_set(self, monkeypatch):
        monkeypatch.setenv("SP_MCP_SKIP_SECURITY_CHECKS", "1")
        monkeypatch.delenv("SP_MCP_ENV", raising=False)
        admc = mock_admc()
        _validate_session_security(admc, _cfg())  # must not raise


# ─────────────────────────────────────────────────────────────────────────────
# CRED-3: check_env_file_permissions
# ─────────────────────────────────────────────────────────────────────────────

class TestEnvFilePermissions:
    """CRED-3 — .env file permission enforcement."""

    def test_rejects_world_readable_env(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text(f"SP_ADMIN_ID={SVC_ADMIN_ID}\n")
        env.chmod(0o644)
        with pytest.raises(SystemExit) as exc:
            check_env_file_permissions(str(env))
        assert exc.value.code == 1

    def test_rejects_group_readable_env(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text(f"SP_ADMIN_ID={SVC_ADMIN_ID}\n")
        env.chmod(0o640)
        with pytest.raises(SystemExit) as exc:
            check_env_file_permissions(str(env))
        assert exc.value.code == 1

    def test_accepts_owner_only_env(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text(f"SP_ADMIN_ID={SVC_ADMIN_ID}\n")
        env.chmod(0o600)
        check_env_file_permissions(str(env))  # must not raise

    def test_accepts_missing_env(self, tmp_path):
        """Missing .env is fine — env vars may come from the OS environment."""
        check_env_file_permissions(str(tmp_path / ".env"))  # does not exist


# ─────────────────────────────────────────────────────────────────────────────
# RG-2: secure_startup combines permission check + dotenv
# ─────────────────────────────────────────────────────────────────────────────

class TestSecureStartup:
    """RG-2 — secure_startup() is atomic guard + loader."""

    def test_secure_startup_rejects_insecure_env(self, tmp_path):
        env = tmp_path / ".env"
        env.write_text(f"SP_ADMIN_ID={SVC_ADMIN_ID}\n")
        env.chmod(0o644)
        with pytest.raises(SystemExit):
            secure_startup(str(env))

    def test_secure_startup_loads_env_when_permissions_ok(self, tmp_path, monkeypatch):
        env = tmp_path / ".env"
        env.write_text("SP_TEST_VAR=hello\n")
        env.chmod(0o600)
        monkeypatch.delenv("SP_TEST_VAR", raising=False)
        secure_startup(str(env))
        assert os.environ.get("SP_TEST_VAR") == "hello"


# ─────────────────────────────────────────────────────────────────────────────
# ACC-2: privilege-filtered tool registration
# ─────────────────────────────────────────────────────────────────────────────

class TestPrivilegeFiltering:
    """ACC-2 — only tools matching account privilege are registered."""

    def test_system_account_satisfies_all_tiers(self):
        from sp_mcp_server.mcp_factory import _PRIVILEGE_SATISFIES
        satisfies = _PRIVILEGE_SATISFIES["system"]
        assert "system" in satisfies
        assert "policy" in satisfies
        assert "storage" in satisfies
        assert "operator" in satisfies
        assert "any" in satisfies

    def test_operator_account_does_not_satisfy_policy(self):
        from sp_mcp_server.mcp_factory import _PRIVILEGE_SATISFIES
        satisfies = _PRIVILEGE_SATISFIES["operator"]
        assert "policy" not in satisfies
        assert "system" not in satisfies
        assert "operator" in satisfies
        assert "any" in satisfies

    def test_any_account_only_satisfies_any(self):
        from sp_mcp_server.mcp_factory import _PRIVILEGE_SATISFIES
        assert _PRIVILEGE_SATISFIES["any"] == {"any"}

    def test_parse_sp_privilege_returns_system(self):
        from sp_mcp_server.mcp_factory import _parse_sp_privilege
        assert _parse_sp_privilege(SP_OUTPUT_PRIVILEGE_SYSTEM) == "system"

    def test_parse_sp_privilege_returns_operator(self):
        from sp_mcp_server.mcp_factory import _parse_sp_privilege
        assert _parse_sp_privilege(SP_OUTPUT_PRIVILEGE_OPERATOR) == "operator"

    def test_parse_sp_privilege_returns_any_when_no_class(self):
        from sp_mcp_server.mcp_factory import _parse_sp_privilege
        assert _parse_sp_privilege(SP_OUTPUT_PRIVILEGE_NONE) == "any"


# ─────────────────────────────────────────────────────────────────────────────
# POL-3: _check_lockout_policy
# ─────────────────────────────────────────────────────────────────────────────

class TestLockoutPolicy:
    """POL-3 — startup lockout threshold warning."""

    def test_warns_when_limit_is_zero(self, caplog):
        admc = mock_admc(stdout=SP_OUTPUT_LOCKOUT_ZERO, code=0)
        with caplog.at_level(logging.WARNING):
            _check_lockout_policy(admc)
        assert any(
            "POL-3" in r.message or "lockout" in r.message.lower()
            for r in caplog.records
        )

    def test_logs_ok_when_limit_is_set(self, caplog):
        admc = mock_admc(stdout=SP_OUTPUT_LOCKOUT_FIVE, code=0)
        with caplog.at_level(logging.INFO):
            _check_lockout_policy(admc)
        warnings = [r for r in caplog.records if r.levelno >= logging.WARNING]
        assert len(warnings) == 0

    def test_warns_when_query_fails(self, caplog):
        admc = mock_admc(stdout="", stderr=SP_OUTPUT_CONN_FAILED_STDERR, code=1)
        with caplog.at_level(logging.WARNING):
            _check_lockout_policy(admc)
        assert any(r.levelno >= logging.WARNING for r in caplog.records)
