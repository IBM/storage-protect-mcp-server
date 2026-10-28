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


def test_dsmadmc_execute_silent_passes_server_stanza(monkeypatch):
    """NET-3: execute_silent must target the same SERVERNAME stanza as execute."""
    captured = {}

    class Result:
        stdout = ""
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    monkeypatch.setenv("SP_SERVER_NAME", "SERVER1")

    wrapper = DsmAdmcWrapper(make_server_config())
    wrapper.execute_silent(CMD_QUERY_STATUS)

    assert "-SE=SERVER1" in captured["args"]
    assert f"-PA={ADMIN_PASSWORD}" in captured["args"]


def test_dsmadmc_execute_does_not_log_command_or_password(monkeypatch, caplog):
    """Command strings may embed passwords; only the verb may be logged."""
    class Result:
        stdout = ""
        stderr = ""
        returncode = 0

    monkeypatch.setattr("subprocess.run", lambda *a, **k: Result())

    wrapper = DsmAdmcWrapper(make_server_config())
    with caplog.at_level("DEBUG", logger="sp_mcp_server.cli_wrapper"):
        wrapper.execute("UPDATE NODE N1 s3cretPassw0rd")

    assert "s3cretPassw0rd" not in caplog.text
    assert ADMIN_PASSWORD not in caplog.text
    assert "UPDATE command" in caplog.text
