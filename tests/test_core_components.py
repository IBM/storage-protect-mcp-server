from sp_mcp_server.config import ServerConfig, load_config
from sp_mcp_server.cli_wrapper import DsmAdmcWrapper, DsmServWrapper, ServermonWrapper
from sp_mcp_server.commands.system.server import QueryServerStatus
from sp_mcp_server.commands.servermon import RunServerMon


class DummyCli:
    def __init__(self, stdout="OK", stderr="", code=0):
        self.stdout = stdout
        self.stderr = stderr
        self.code = code
        self.calls = []

    def execute(self, command):
        self.calls.append(command)
        return self.stdout, self.stderr, self.code


def test_load_config_reads_environment(monkeypatch):
    monkeypatch.setenv("TCPSERVERADDRESS", "test.server.com")
    monkeypatch.setenv("SP_SERVER_PORT", "1600")
    monkeypatch.setenv("SP_ADMIN_ID", "admin")
    monkeypatch.setenv("SP_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SP_DSMSERV_PATH", "/opt/tivoli/tsm/server/bin/dsmserv")
    monkeypatch.setenv("SP_SERVER_INSTANCE_DIR", "/home/tsminst1")
    monkeypatch.setenv("SP_SERVERMON_PATH", "/opt/tivoli/tsm/server/bin/servermon")
    monkeypatch.setenv("SP_SERVERMON_XML_DIR", "/tmp/servermon")
    monkeypatch.setenv("SP_INSTANCE_USER", "tsminst1")

    config = load_config()

    assert config.server_address == "test.server.com"
    assert config.server_port == "1600"
    assert config.admin_id == "admin"
    assert config.admin_password == "secret"
    assert config.dsmserv_path == "/opt/tivoli/tsm/server/bin/dsmserv"
    assert config.server_instance_dir == "/home/tsminst1"
    assert config.servermon_path == "/opt/tivoli/tsm/server/bin/servermon"
    assert config.servermon_xml_dir == "/tmp/servermon"
    assert config.instance_user == "tsminst1"


def test_server_config_validate_requires_credentials():
    valid = ServerConfig(
        server_address=None,
        server_port="1500",
        admin_id="admin",
        admin_password="secret",
    )
    invalid = ServerConfig(
        server_address=None,
        server_port="1500",
        admin_id="admin",
        admin_password=None,
    )

    assert valid.validate() is True
    assert invalid.validate() is False


def test_dsmadmc_wrapper_returns_config_error_when_credentials_missing():
    config = ServerConfig(
        server_address="server.example.com",
        server_port="1500",
        admin_id=None,
        admin_password=None,
    )

    wrapper = DsmAdmcWrapper(config)
    stdout, stderr, code = wrapper.execute("QUERY STATUS")

    assert stdout == ""
    assert "Configuration incomplete" in stderr
    assert code == 1


def test_dsmserv_wrapper_uses_instance_user(monkeypatch):
    captured = {}

    class Result:
        stdout = "offline ok"
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    config = ServerConfig(
        server_address=None,
        server_port="1500",
        admin_id="admin",
        admin_password="secret",
        dsmserv_path="/bin/dsmserv",
        server_instance_dir="/home/tsminst1",
        instance_user="tsminst1",
    )

    wrapper = DsmServWrapper(config)
    stdout, stderr, code = wrapper.execute("DISPLAY DBSPACE")

    assert stdout == "offline ok"
    assert stderr == ""
    assert code == 0
    assert captured["args"][0:3] == ["su", "-", "tsminst1"]
    assert "/bin/dsmserv -i /home/tsminst1 DISPLAY DBSPACE" in captured["args"][4]


def test_servermon_wrapper_returns_existing_output_when_busy(monkeypatch, tmp_path):
    xml_root = tmp_path / "srvmon"
    results_dir = xml_root / ".20260306T1159-SERVER1" / "results"
    results_dir.mkdir(parents=True)
    xml_file = results_dir / "summary.xml"
    xml_file.write_text("<servermon>ready</servermon>")

    config = ServerConfig(
        server_address=None,
        server_port="1500",
        admin_id="admin",
        admin_password="secret",
        servermon_path="/bin/servermon",
        servermon_xml_dir=str(xml_root),
        instance_user="tsminst1",
    )

    wrapper = ServermonWrapper(config)
    monkeypatch.setattr(wrapper, "_check_servermon_running", lambda: True)

    stdout, stderr, code = wrapper.execute(["-standard"])

    assert code == 0
    assert stderr == ""
    assert "Using existing servermon diagnostics from:" in stdout
    assert "<servermon>ready</servermon>" in stdout


def test_query_server_status_executes_expected_command():
    cli = DummyCli(stdout="STATUS OK")
    cmd = QueryServerStatus(cli)

    result = cmd.execute({})

    assert cli.calls == ["QUERY STATUS"]
    assert result == "STATUS OK"


def test_run_servermon_passes_args_to_wrapper():
    cli = DummyCli(stdout="SERVERMON OK")
    cmd = RunServerMon(cli)

    result = cmd.execute({"args": ["-standard", "-dbonly"]})

    assert cli.calls == [["-standard", "-dbonly"]]
    assert result == "SERVERMON OK"
