import os
import sys
import json
import pytest
from sp_mcp_server.mcp_factory import reset_execution_state


@pytest.fixture(autouse=True)
def clean_test_execution_state():
    """
    AUD-F-01: Ensure clean ContextVar and module-level execution state for every test.
    Resets current_audit_user, current_session_id, current_execution_credentials,
    current_auth_model, _process_session_id, _process_audit_user, and clears the session manager.
    """
    reset_execution_state()
    yield
    reset_execution_state()


def pytest_sessionfinish(session, exitstatus):
    """
    Automatically populate Allure report environment metadata and defect categories.
    """
    allure_dir = session.config.getoption("--alluredir", default="allure-results")
    if not allure_dir:
        allure_dir = "allure-results"

    if os.path.exists(allure_dir) or not os.path.isabs(allure_dir):
        os.makedirs(allure_dir, exist_ok=True)
        # 1. Write environment.properties
        env_file = os.path.join(allure_dir, "environment.properties")
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"System.OS={sys.platform}\n")
                f.write(f"Python.Version={sys.version.split()[0]}\n")
                f.write("Server.Name=IBM Storage Protect MCP Server\n")
                f.write("Server.Version=1.0.0\n")
                f.write("Security.SessionSecurity=STRICT\n")
                f.write("Security.TierHierarchy=5-Tier (System/Policy/Storage/Operator/ReadOnly)\n")
                f.write("Security.AuditMode=Strict (SP_MCP_STRICT_AUDIT=1)\n")
                f.write("QualityGates.Status=QG-1 through QG-9 Enforced\n")
        except Exception:
            pass

        # 2. Write categories.json
        cat_file = os.path.join(allure_dir, "categories.json")
        try:
            categories = [
                {
                    "name": "Security Invariant Breaches",
                    "matchedStatuses": ["failed"],
                    "messageRegex": ".*(AUTHORIZATION_DENIED|DUAL_CUSTODY|SESSIONSECURITY|PermissionError).*",
                },
                {
                    "name": "Subprocess & Environmental Failures",
                    "matchedStatuses": ["failed"],
                    "messageRegex": ".*(ANS1017E|ANS1025E|ANS1353E|TimeoutExpired|ENOSPC).*",
                },
                {
                    "name": "Platform Conditional Skips",
                    "matchedStatuses": ["skipped"],
                    "messageRegex": ".*POSIX.*",
                },
                {
                    "name": "Live Integration Stubs",
                    "matchedStatuses": ["skipped"],
                    "messageRegex": ".*live.*",
                },
            ]
            with open(cat_file, "w", encoding="utf-8") as f:
                json.dump(categories, f, indent=2)
        except Exception:
            pass

