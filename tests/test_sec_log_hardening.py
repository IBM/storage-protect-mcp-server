"""
Regression tests: plaintext passwords persisted by the transport log.

Root causes covered:
  1. Root logger at DEBUG let the MCP SDK's SSE transport write every raw POST
     body (``Received JSON: b'...'``) to the persistent log before authorization.
  2. Log files/dirs were created world-readable (0644/0755) and the /tmp
     fallback path was predictable and not validated.
"""

import json
import logging
import os
import stat
import threading
import time
from unittest.mock import MagicMock

import httpx
import pytest

import sp_mcp_server.mcp_factory as factory
from sp_mcp_server.commands.system.admin import DeleteAdmin
from tests.fixtures import (
    SP_OUTPUT_SESSION_STRICT_TLS13,
    SVC_ADMIN_ID,
    make_config_with_cred,
)

SECRET = "Zx9!SentinelPassw0rd#4417"


def _mode(path) -> int:
    return stat.S_IMODE(os.stat(path).st_mode)


def _flush():
    for h in logging.getLogger().handlers:
        h.flush()


@pytest.fixture
def log_env(tmp_path, monkeypatch):
    """Isolated, restorable logging state; yields the primary log directory."""
    root = logging.getLogger()
    saved_level = root.level
    saved_handlers = list(root.handlers)
    saved_quiet = {n: logging.getLogger(n).level for n in factory._QUIET_LOGGERS}

    log_dir = tmp_path / "logs"
    monkeypatch.setenv("SP_MCP_LOG_DIR", str(log_dir))
    monkeypatch.delenv("SP_MCP_LOG_LEVEL", raising=False)
    monkeypatch.setattr(factory.tempfile, "gettempdir", lambda: str(tmp_path / "tmp"))
    (tmp_path / "tmp").mkdir()
    old_umask = os.umask(0o022)  # the permissive umask from the report

    yield log_dir

    os.umask(old_umask)
    for h in list(root.handlers):
        if h not in saved_handlers:
            root.removeHandler(h)
            h.close()
    root.setLevel(saved_level)
    for n, lvl in saved_quiet.items():
        logging.getLogger(n).setLevel(lvl)


# ── permissions ──────────────────────────────────────────────────────────────

def test_log_dir_0700_and_file_0600_under_permissive_umask(log_env):
    factory.setup_logging()
    logging.getLogger("ibm-sp-mcp-server").info("hello")
    _flush()
    assert _mode(log_env) == 0o700
    assert _mode(log_env / "mcp-server.log") == 0o600


def test_existing_loose_log_and_backups_are_tightened(log_env):
    log_env.mkdir()
    for name in ("mcp-server.log", "mcp-server.log.1", "mcp-server.log.3"):
        p = log_env / name
        p.write_text("old\n")
        p.chmod(0o644)
    factory.setup_logging()
    for name in ("mcp-server.log", "mcp-server.log.1", "mcp-server.log.3"):
        assert _mode(log_env / name) == 0o600, name


def test_rotation_recreates_base_file_as_0600(log_env):
    factory.setup_logging()
    handler = next(
        h for h in logging.getLogger().handlers
        if isinstance(h, factory._SecureRotatingFileHandler)
    )
    logging.getLogger("ibm-sp-mcp-server").info("before rotate")
    handler.doRollover()
    logging.getLogger("ibm-sp-mcp-server").info("after rotate")
    _flush()
    assert _mode(log_env / "mcp-server.log") == 0o600
    assert _mode(log_env / "mcp-server.log.1") == 0o600


def test_setup_logging_is_idempotent(log_env):
    factory.setup_logging()
    factory.setup_logging()
    tagged = [h for h in logging.getLogger().handlers if getattr(h, factory._SP_HANDLER_ATTR, False)]
    assert len(tagged) == 2  # one file + one stderr


# ── /tmp fallback ────────────────────────────────────────────────────────────

def test_fallback_is_per_uid_private_dir(log_env, tmp_path):
    (tmp_path / "not-a-dir").write_text("x")
    os.environ["SP_MCP_LOG_DIR"] = str(tmp_path / "not-a-dir")  # unusable primary
    factory.setup_logging()
    logging.getLogger("ibm-sp-mcp-server").info("to fallback")
    _flush()
    fb = factory._fallback_log_dir()
    assert os.path.basename(fb) != "ibm-sp-mcp-server"  # not the predictable name
    assert _mode(fb) == 0o700
    assert _mode(os.path.join(fb, "mcp-server.log")) == 0o600
    assert "to fallback" in open(os.path.join(fb, "mcp-server.log")).read()


def test_fallback_refuses_planted_symlink(log_env, tmp_path):
    (tmp_path / "not-a-dir").write_text("x")
    os.environ["SP_MCP_LOG_DIR"] = str(tmp_path / "not-a-dir")
    victim = tmp_path / "attacker-controlled"
    victim.mkdir()
    os.symlink(victim, factory._fallback_log_dir())
    factory.setup_logging()
    logging.getLogger("ibm-sp-mcp-server").info("must not land in symlink target")
    _flush()
    assert list(victim.iterdir()) == []
    assert not any(
        isinstance(h, factory._SecureRotatingFileHandler) for h in logging.getLogger().handlers
    )


def test_fallback_existing_loose_dir_is_tightened(log_env, tmp_path):
    (tmp_path / "not-a-dir").write_text("x")
    os.environ["SP_MCP_LOG_DIR"] = str(tmp_path / "not-a-dir")
    fb = factory._fallback_log_dir()
    os.mkdir(fb)
    os.chmod(fb, 0o777)
    factory.setup_logging()
    assert _mode(fb) == 0o700


# ── level policy ─────────────────────────────────────────────────────────────

def test_root_not_debug_and_sdk_loggers_quiet(log_env):
    factory.setup_logging()
    assert logging.getLogger().level == logging.INFO
    assert not logging.getLogger("mcp.server.sse").isEnabledFor(logging.DEBUG)
    assert not logging.getLogger("mcp.server.lowlevel.server").isEnabledFor(logging.DEBUG)


def test_sdk_stays_quiet_even_if_operator_requests_debug(log_env, monkeypatch):
    monkeypatch.setenv("SP_MCP_LOG_LEVEL", "DEBUG")
    factory.setup_logging()
    assert logging.getLogger().level == logging.DEBUG
    sse_log = logging.getLogger("mcp.server.sse")
    assert not sse_log.isEnabledFor(logging.DEBUG)
    sse_log.debug("Received JSON: %r", SECRET)
    _flush()
    assert SECRET not in (log_env / "mcp-server.log").read_text()


# ── redaction backstop ───────────────────────────────────────────────────────

@pytest.mark.parametrize(
    "message",
    [
        'Received JSON: b\'{"jsonrpc":"2.0","params":{"arguments":{"password":"%s"}}}\'',
        "Validated client message: {'arguments': {'password': '%s'}}",
        "args admin_password=%s other=1",
        '{"new_password": "%s", "admin_name": "bob"}',
        "Authorization: Bearer %s",
        "token: %s",
    ],
)
def test_redaction_filter_scrubs_credentials(log_env, message):
    factory.setup_logging()
    logging.getLogger("ibm-sp-mcp-server").info(message % SECRET)
    _flush()
    text = (log_env / "mcp-server.log").read_text()
    assert SECRET not in text
    assert factory._REDACTED in text


def test_redaction_leaves_ordinary_messages_alone(log_env):
    factory.setup_logging()
    msg = "POL-4: Tool 'define_server' completed. SP ACTLOG correlation key: abc123"
    logging.getLogger("ibm-sp-mcp-server").info(msg)
    _flush()
    assert msg in (log_env / "mcp-server.log").read_text()


def test_redaction_handles_lazy_args(log_env):
    factory.setup_logging()
    logging.getLogger("ibm-sp-mcp-server").info("payload %s", {"password": SECRET})
    _flush()
    assert SECRET not in (log_env / "mcp-server.log").read_text()


# ── end to end: real SDK SSE transport ───────────────────────────────────────

def _build_sse_app():
    from mcp.server.sse import SseServerTransport
    from starlette.applications import Starlette
    from starlette.responses import Response
    from starlette.routing import Mount, Route

    cfg = make_config_with_cred(admin_id=SVC_ADMIN_ID)
    admc = MagicMock()
    admc.config = cfg
    admc.execute.return_value = (SP_OUTPUT_SESSION_STRICT_TLS13, "", 0)
    server = factory.create_mcp_server(
        server_name="test-server", tool_classes=[DeleteAdmin], admc_cli=admc, config=cfg
    )
    sse = SseServerTransport("/messages/")

    async def handle_sse(request):
        async with sse.connect_sse(request.scope, request.receive, request._send) as streams:
            await server.run(streams[0], streams[1], server.create_initialization_options())
        return Response()

    return Starlette(routes=[
        Route("/sse", endpoint=handle_sse),
        Mount("/messages/", app=sse.handle_post_message),
    ])


def _post_password_bearing_request() -> None:
    """Run the real SSE transport and POST a password-bearing tools/call to it."""
    import uvicorn

    config = uvicorn.Config(
        _build_sse_app(), host="127.0.0.1", port=0, log_level="warning",
        timeout_graceful_shutdown=1,
    )
    uv = uvicorn.Server(config)
    thread = threading.Thread(target=uv.run, daemon=True)
    thread.start()
    deadline = time.time() + 10
    while not uv.started and time.time() < deadline:
        time.sleep(0.05)
    assert uv.started, "uvicorn did not start"
    port = uv.servers[0].sockets[0].getsockname()[1]
    base = f"http://127.0.0.1:{port}"

    body = {
        "jsonrpc": "2.0", "id": 1, "method": "tools/call",
        "params": {"name": "define_server",  # not registered -> rejected pre-dispatch
                   "arguments": {"server_name": "S1", "password": SECRET}},
    }
    try:
        with httpx.Client(timeout=5) as client:
            with client.stream("GET", f"{base}/sse") as stream:
                endpoint = None
                # Keep a reference: dropping the iterator after `break` would
                # close the response and end the SSE session before we POST.
                lines = stream.iter_lines()
                for line in lines:
                    if line.startswith("data:"):
                        endpoint = line.split("data:", 1)[1].strip()
                        break
                assert endpoint, "no endpoint event received"
                resp = client.post(f"{base}{endpoint}", content=json.dumps(body),
                                   headers={"content-type": "application/json"})
                assert resp.status_code == 202, resp.text
                time.sleep(0.3)  # let the server task process the message
    except (httpx.RemoteProtocolError, httpx.ReadError):
        # Some SDK versions abort the SSE stream when a tools/call arrives before
        # `initialize`; the body was already logged (or not) by then.
        pass
    finally:
        uv.should_exit = True
        thread.join(timeout=5)


def test_control_old_configuration_leaks_sdk_body(log_env, tmp_path):
    """Proves the E2E harness can see the leak: root DEBUG + plain file handler."""
    leak_file = tmp_path / "old-style.log"
    handler = logging.FileHandler(leak_file)
    handler.setLevel(logging.DEBUG)
    root = logging.getLogger()
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    logging.getLogger("mcp").setLevel(logging.NOTSET)
    try:
        _post_password_bearing_request()
        handler.flush()
    finally:
        root.removeHandler(handler)
        handler.close()
    assert SECRET in leak_file.read_text(), "harness no longer reproduces the original leak"


@pytest.mark.parametrize("debug_requested", [False, True])
def test_sse_post_body_never_reaches_log(log_env, monkeypatch, debug_requested):
    if debug_requested:
        monkeypatch.setenv("SP_MCP_LOG_LEVEL", "DEBUG")
    factory.setup_logging()
    _post_password_bearing_request()
    _flush()
    log_text = (log_env / "mcp-server.log").read_text()
    assert SECRET not in log_text
    assert "Received JSON" not in log_text
    assert _mode(log_env / "mcp-server.log") == 0o600


# ── startup warning for pre-fix log files ────────────────────────────────────

def test_warns_when_loose_legacy_log_found(log_env):
    log_env.mkdir()
    old = log_env / "mcp-server.log"
    old.write_text("old\n")
    old.chmod(0o644)
    factory.setup_logging()
    _flush()
    text = old.read_text()
    assert "may contain plaintext credentials" in text
    assert str(old) in text
    assert _mode(old) == 0o600


def test_warns_when_old_predictable_fallback_dir_exists(log_env, tmp_path):
    legacy = tmp_path / "tmp" / "ibm-sp-mcp-server"
    legacy.mkdir()
    (legacy / "mcp-server.log").write_text("old\n")
    factory.setup_logging()
    _flush()
    assert str(legacy / "mcp-server.log") in (log_env / "mcp-server.log").read_text()


def test_no_legacy_warning_on_clean_start_or_restart(log_env):
    factory.setup_logging()
    logging.getLogger("ibm-sp-mcp-server").info("first run")
    _flush()
    factory.setup_logging()  # restart: file is now 0600, so no warning
    _flush()
    assert "may contain plaintext credentials" not in (log_env / "mcp-server.log").read_text()
