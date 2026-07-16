from sp_mcp_server.cli_wrapper import DsmAdmcWrapper, DsmServWrapper, ServermonWrapper
from sp_mcp_server.config import ServerConfig


def make_config():
    return ServerConfig(
        server_address="test.server.com",
        server_port="1500",
        admin_id="admin",
        admin_password="password",
        dsmserv_path="/bin/dsmserv",
        servermon_path="/bin/servermon",
        servermon_xml_dir="/tmp/servermon",
        instance_user="tsminst1",
    )


def test_dsmadmc_execute_success(monkeypatch):
    captured = {}

    class Result:
        stdout = "Output data"
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    wrapper = DsmAdmcWrapper(make_config())
    stdout, stderr, code = wrapper.execute("QUERY STATUS")

    assert stdout == "Output data"
    assert stderr == ""
    assert code == 0
    assert captured["args"][0].endswith("dsmadmc")
    assert "-NOConfirm" in captured["args"]
    assert "-DATAONLY=YES" in captured["args"]
    assert "-COMMAdelimited" in captured["args"]
    assert "-ID=admin" in captured["args"]
    assert "-PA=password" in captured["args"]
    assert "QUERY" in captured["args"]
    assert "STATUS" in captured["args"]


def test_dsmadmc_execute_file_not_found(monkeypatch):
    def fake_run(args, capture_output, text, check, timeout):
        raise FileNotFoundError()

    monkeypatch.setattr("subprocess.run", fake_run)

    wrapper = DsmAdmcWrapper(make_config())
    stdout, stderr, code = wrapper.execute("QUERY STATUS")

    assert stdout == ""
    assert "dsmadmc executable not found" in stderr
    assert code == 127


def test_dsmserv_execute_without_instance_user(monkeypatch):
    captured = {}

    class Result:
        stdout = "offline ok"
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    config = make_config()
    config.instance_user = None

    wrapper = DsmServWrapper(config)
    stdout, stderr, code = wrapper.execute("DISPLAY DBSPACE")

    assert stdout == "offline ok"
    assert stderr == ""
    assert code == 0
    assert captured["args"] == ["/bin/dsmserv", "DISPLAY", "DBSPACE"]


def test_servermon_execute_runs_command(monkeypatch):
    captured = {}

    class Result:
        stdout = "servermon ok"
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    wrapper = ServermonWrapper(make_config())
    monkeypatch.setattr(wrapper, "_check_servermon_running", lambda: False)

    stdout, stderr, code = wrapper.execute(["-standard"])

    assert stdout == "servermon ok"
    assert stderr == ""
    assert code == 0
    assert captured["args"][0:3] == ["su", "-", "tsminst1"]
    assert "/bin/servermon -standard" in captured["args"][4]


def test_servermon_returns_busy_error_when_no_existing_output(monkeypatch):
    wrapper = ServermonWrapper(make_config())
    monkeypatch.setattr(wrapper, "_check_servermon_running", lambda: True)
    monkeypatch.setattr(wrapper, "_get_latest_servermon_output", lambda: None)

    stdout, stderr, code = wrapper.execute(["-standard"])

    assert stdout == ""
    assert "Another servermon instance is currently running" in stderr
    assert code == 1
