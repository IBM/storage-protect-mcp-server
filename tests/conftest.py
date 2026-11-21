"""
Pytest configuration and global hooks for the test suite.
"""

import sys

# Windows sandbox shim:
# On Windows, Python's asyncio ProactorEventLoop uses a loopback socket pair for its self-pipe.
# In sandboxed / restricted test environments without loopback network permissions,
# socket._fallback_socketpair hangs indefinitely on accept().
# We patch BaseProactorEventLoop with an in-memory dummy pipe and clamp IocpProactor.select
# timeout so that asyncio.run() and asyncio.to_thread() execute cleanly and quickly in
# sandboxed test runs without hanging.
if sys.platform == "win32":
    try:
        import signal
        from asyncio.proactor_events import BaseProactorEventLoop
        from asyncio.windows_events import IocpProactor

        class _DummySock:
            def fileno(self):
                return -1

            def setblocking(self, b):
                pass

            def close(self):
                pass

        def _fake_make_self_pipe(self):
            self._ssock = _DummySock()
            self._csock = _DummySock()
            self._internal_fds += 1

        orig_select = IocpProactor.select

        def _clamped_select(self, timeout=None):
            if timeout is None or timeout > 0.05:
                timeout = 0.05
            return orig_select(self, timeout)

        orig_set_wakeup = signal.set_wakeup_fd
        signal.set_wakeup_fd = lambda fd: -1 if fd == -1 else orig_set_wakeup(fd)

        BaseProactorEventLoop._make_self_pipe = _fake_make_self_pipe
        BaseProactorEventLoop._loop_self_reading = lambda self, f=None: None
        BaseProactorEventLoop._write_to_self = lambda self: None
        IocpProactor.select = _clamped_select
    except Exception:
        pass

import pytest


def pytest_collection_modifyitems(config, items):
    if sys.platform == "win32":
        skip_posix = pytest.mark.skip(
            reason="POSIX mode bits (0600/0700) and live loopback sockets require Linux/Unix environment"
        )
        posix_only_tests = {
            "test_log_dir_0700_and_file_0600_under_permissive_umask",
            "test_existing_loose_log_and_backups_are_tightened",
            "test_rotation_recreates_base_file_as_0600",
            "test_fallback_is_per_uid_private_dir",
            "test_fallback_refuses_planted_symlink",
            "test_fallback_existing_loose_dir_is_tightened",
            "test_control_old_configuration_leaks_sdk_body",
            "test_sse_post_body_never_reaches_log",
            "test_warns_when_loose_legacy_log_found",
            "test_no_legacy_warning_on_clean_start_or_restart",
            "test_accepts_owner_only_env",
            "test_secure_startup_loads_env_when_permissions_ok",
            "test_rejects_world_readable_env",
            "test_rejects_group_readable_env",
            "test_secure_startup_rejects_insecure_env",
        }
        for item in items:
            test_name = item.name.split("[")[0]
            if test_name in posix_only_tests:
                item.add_marker(skip_posix)


def pytest_sessionfinish(session, exitstatus):
    """
    Allure report generation hook:
    1. Injects environment metadata and failure categories into the Allure results directory.
    2. Automatically compiles the standalone HTML Allure report if the Allure CLI is installed.
    """
    import os
    import json
    import shutil
    import subprocess

    alluredir = getattr(session.config.option, "allure_report_dir", None) or "allure-results"
    if not os.path.isabs(alluredir):
        alluredir = os.path.abspath(alluredir)

    if os.path.isdir(alluredir):
        # 1. Write environment metadata
        env_file = os.path.join(alluredir, "environment.properties")
        try:
            with open(env_file, "w", encoding="utf-8") as f:
                f.write(f"Platform={sys.platform}\n")
                f.write(f"Python.Version={sys.version.split()[0]}\n")
                f.write("Project=ibm-storage-protect-mcp-server\n")
                f.write("TestFramework=pytest-allure\n")
                f.write("SecurityControls=OA-8,DAUTH-10,DAUTH-11,ACC-3,POL-4,NET-1,RG-1,CRED-3\n")
                f.write("Vulnerabilities=VUL0790479,VUL0790697\n")
        except Exception:
            pass

        # 2. Write custom categories for defect classification
        categories_file = os.path.join(alluredir, "categories.json")
        try:
            categories = [
                {
                    "name": "Security Authorization Denials",
                    "matchedStatuses": ["failed"],
                    "messageRegex": ".*AUTHORIZATION_DENIED.*|.*AUTHENTICATION_REQUIRED.*|.*Forbidden.*",
                },
                {
                    "name": "Platform Compatibility Skips",
                    "matchedStatuses": ["skipped"],
                    "messageRegex": ".*POSIX.*",
                },
            ]
            with open(categories_file, "w", encoding="utf-8") as f:
                json.dump(categories, f, indent=2)
        except Exception:
            pass

        # 3. Automatically compile HTML report if allure CLI binary is found
        allure_cmd = shutil.which("allure")
        if allure_cmd:
            report_dir = os.environ.get("ALLURE_REPORT_DIR", "allure-report")
            try:
                subprocess.run(
                    ["allure", "generate", alluredir, "-o", report_dir, "--clean"],
                    shell=True,
                    check=False,
                    capture_output=True,
                )
            except Exception:
                pass
