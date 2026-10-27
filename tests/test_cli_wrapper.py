from sp_mcp_server.cli_wrapper import DsmAdmcWrapper, DsmServWrapper, ServermonWrapper

from tests.fixtures import (
    make_server_config,
    ADMIN_ID,
    ADMIN_PASSWORD,
    SP_INSTANCE_USER,
    DSMSERV_PATH,
    SERVERMON_PATH,
    SP_OUTPUT_QUERY_OUTPUT,
    SP_OUTPUT_OFFLINE_OK,
    SP_OUTPUT_SERVERMON_PLAIN,
    CMD_QUERY_STATUS,
    CMD_DISPLAY_DBSPACE,
    SERVERMON_ARGS_STANDARD,
)


def test_dsmadmc_execute_success(monkeypatch):
    captured = {}

    class Result:
        stdout = SP_OUTPUT_QUERY_OUTPUT
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    wrapper = DsmAdmcWrapper(make_server_config())
    stdout, stderr, code = wrapper.execute(CMD_QUERY_STATUS)

    assert stdout == SP_OUTPUT_QUERY_OUTPUT
    assert stderr == ""
    assert code == 0
    assert captured["args"][0].endswith("dsmadmc")
    assert "-NOConfirm" in captured["args"]
    assert "-DATAONLY=YES" in captured["args"]
    assert "-COMMAdelimited" in captured["args"]
    assert f"-ID={ADMIN_ID}" in captured["args"]
    assert f"-PA={ADMIN_PASSWORD}" in captured["args"]
    assert "QUERY" in captured["args"]
    assert "STATUS" in captured["args"]


def test_dsmadmc_execute_file_not_found(monkeypatch):
    def fake_run(args, capture_output, text, check, timeout):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", fake_run)

    wrapper = DsmAdmcWrapper(make_server_config())
    stdout, stderr, code = wrapper.execute(CMD_QUERY_STATUS)

    assert stdout == ""
    assert "dsmadmc executable not found" in stderr
    assert code == 127


def test_dsmserv_execute_without_instance_user(monkeypatch):
    captured = {}

    class Result:
        stdout = SP_OUTPUT_OFFLINE_OK
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    config = make_server_config(instance_user=None)

    wrapper = DsmServWrapper(config)
    stdout, stderr, code = wrapper.execute(CMD_DISPLAY_DBSPACE)

    assert stdout == SP_OUTPUT_OFFLINE_OK
    assert stderr == ""
    assert code == 0
    assert captured["args"] == [DSMSERV_PATH, "DISPLAY", "DBSPACE"]


def test_servermon_execute_runs_command(monkeypatch):
    captured = {}

    class Result:
        stdout = SP_OUTPUT_SERVERMON_PLAIN
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    wrapper = ServermonWrapper(make_server_config())
    monkeypatch.setattr(wrapper, "_check_servermon_running", lambda: False)

    stdout, stderr, code = wrapper.execute(SERVERMON_ARGS_STANDARD)

    assert stdout == SP_OUTPUT_SERVERMON_PLAIN
    assert stderr == ""
    assert code == 0
    # ACC-4: sudo -u <user> -- used instead of su - <user> -c <cmd>
    assert captured["args"][0:4] == ["sudo", "-u", SP_INSTANCE_USER, "--"]
    assert captured["args"][4] == SERVERMON_PATH
    assert SERVERMON_ARGS_STANDARD[0] in captured["args"]


def test_servermon_returns_busy_error_when_no_existing_output(monkeypatch):
    wrapper = ServermonWrapper(make_server_config())
    monkeypatch.setattr(wrapper, "_check_servermon_running", lambda: True)
    monkeypatch.setattr(wrapper, "_get_latest_servermon_output", lambda: None)

    stdout, stderr, code = wrapper.execute(SERVERMON_ARGS_STANDARD)

    assert stdout == ""
    assert "Another servermon instance is currently running" in stderr
    assert code == 1
