from sp_mcp_server.config import ServerConfig, load_config
from sp_mcp_server.cli_wrapper import DsmAdmcWrapper, DsmServWrapper, ServermonWrapper
from sp_mcp_server.commands.system.server import QueryServerStatus
from sp_mcp_server.commands.servermon import RunServerMon

from tests.fixtures import (
    FakeAdmcCli,
    FakeServermonCli,
    make_server_config,
    # server / network
    SP_TEST_SERVER_ADDRESS,
    SP_ALT_SERVER_PORT,
    SP_SERVER_PORT,
    # credentials
    ADMIN_ID,
    ADMIN_PASSWORD,
    SP_INSTANCE_USER,
    SP_INSTANCE_DIR,
    DSMSERV_PATH,
    DSMSERV_PATH_FULL,
    SERVERMON_PATH,
    SERVERMON_PATH_FULL,
    SERVERMON_XML_DIR,
    # command outputs
    SP_OUTPUT_STATUS_OK,
    SP_OUTPUT_SERVERMON_OK,
    SP_OUTPUT_OFFLINE_OK,
    SERVERMON_XML_CONTENT,
    SERVERMON_SUBDIR_NAME,
    # commands
    CMD_QUERY_STATUS,
    CMD_DISPLAY_DBSPACE,
    SERVERMON_ARGS_STANDARD,
    SERVERMON_ARGS_STANDARD_DBONLY,
)


# ---------------------------------------------------------------------------
# Config tests
# ---------------------------------------------------------------------------


def test_load_config_reads_environment(monkeypatch):
    monkeypatch.setenv("TCPSERVERADDRESS", SP_TEST_SERVER_ADDRESS)
    monkeypatch.setenv("SP_SERVER_PORT", SP_ALT_SERVER_PORT)
    monkeypatch.setenv("SP_ADMIN_ID", ADMIN_ID)
    monkeypatch.setenv("SP_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("SP_DSMSERV_PATH", DSMSERV_PATH_FULL)
    monkeypatch.setenv("SP_SERVER_INSTANCE_DIR", SP_INSTANCE_DIR)
    monkeypatch.setenv("SP_SERVERMON_PATH", SERVERMON_PATH_FULL)
    monkeypatch.setenv("SP_SERVERMON_XML_DIR", SERVERMON_XML_DIR)
    monkeypatch.setenv("SP_INSTANCE_USER", SP_INSTANCE_USER)

    config = load_config()

    assert config.server_address == SP_TEST_SERVER_ADDRESS
    assert config.server_port == SP_ALT_SERVER_PORT
    assert config.admin_id == ADMIN_ID
    assert config.admin_password == ADMIN_PASSWORD
    assert config.dsmserv_path == DSMSERV_PATH_FULL
    assert config.server_instance_dir == SP_INSTANCE_DIR
    assert config.servermon_path == SERVERMON_PATH_FULL
    assert config.servermon_xml_dir == SERVERMON_XML_DIR
    assert config.instance_user == SP_INSTANCE_USER


def test_server_config_validate_requires_credentials():
    valid = ServerConfig(
        server_address=None,
        server_port=SP_SERVER_PORT,
        admin_id=ADMIN_ID,
        admin_password=ADMIN_PASSWORD,
    )
    invalid = ServerConfig(
        server_address=None,
        server_port=SP_SERVER_PORT,
        admin_id=ADMIN_ID,
        admin_password=None,
    )

    assert valid.validate() is True
    assert invalid.validate() is False


# ---------------------------------------------------------------------------
# Wrapper tests
# ---------------------------------------------------------------------------


def test_dsmadmc_wrapper_returns_config_error_when_credentials_missing():
    config = ServerConfig(
        server_address=SP_TEST_SERVER_ADDRESS,
        server_port=SP_SERVER_PORT,
        admin_id=None,
        admin_password=None,
    )

    wrapper = DsmAdmcWrapper(config)
    stdout, stderr, code = wrapper.execute(CMD_QUERY_STATUS)

    assert stdout == ""
    assert "Configuration incomplete" in stderr
    assert code == 1


def test_dsmserv_wrapper_uses_instance_user(monkeypatch):
    captured = {}

    class Result:
        stdout = SP_OUTPUT_OFFLINE_OK
        stderr = ""
        returncode = 0

    def fake_run(args, capture_output, text, check, timeout):
        captured["args"] = args
        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)

    config = make_server_config(
        server_address=None,
        dsmserv_path=DSMSERV_PATH,
        server_instance_dir=SP_INSTANCE_DIR,
        instance_user=SP_INSTANCE_USER,
    )

    wrapper = DsmServWrapper(config)
    stdout, stderr, code = wrapper.execute(CMD_DISPLAY_DBSPACE)

    assert stdout == SP_OUTPUT_OFFLINE_OK
    assert stderr == ""
    assert code == 0
    # ACC-4: sudo -u <user> -- used instead of su - <user> -c <cmd>
    assert captured["args"][0:4] == ["sudo", "-u", SP_INSTANCE_USER, "--"]
    assert captured["args"][4] == DSMSERV_PATH
    assert "-i" in captured["args"]
    assert "DISPLAY" in captured["args"]
    assert "DBSPACE" in captured["args"]


def test_servermon_wrapper_returns_existing_output_when_busy(monkeypatch, tmp_path):
    xml_root = tmp_path / "srvmon"
    results_dir = xml_root / SERVERMON_SUBDIR_NAME / "results"
    results_dir.mkdir(parents=True)
    xml_file = results_dir / "summary.xml"
    xml_file.write_text(SERVERMON_XML_CONTENT)

    config = make_server_config(
        server_address=None,
        servermon_path=SERVERMON_PATH,
        servermon_xml_dir=str(xml_root),
        instance_user=SP_INSTANCE_USER,
    )

    wrapper = ServermonWrapper(config)
    monkeypatch.setattr(wrapper, "_check_servermon_running", lambda: True)

    stdout, stderr, code = wrapper.execute(SERVERMON_ARGS_STANDARD)

    assert code == 0
    assert stderr == ""
    assert "Using existing servermon diagnostics from:" in stdout
    assert SERVERMON_XML_CONTENT in stdout


# ---------------------------------------------------------------------------
# Command unit tests
# ---------------------------------------------------------------------------


def test_query_server_status_executes_expected_command():
    cli = FakeAdmcCli(stdout=SP_OUTPUT_STATUS_OK)
    cmd = QueryServerStatus(cli)  # type: ignore[arg-type]

    result = cmd.execute({})

    assert cli.calls == [CMD_QUERY_STATUS]
    assert result == SP_OUTPUT_STATUS_OK


def test_run_servermon_passes_args_to_wrapper():
    cli = FakeServermonCli(stdout=SP_OUTPUT_SERVERMON_OK)
    cmd = RunServerMon(cli)  # type: ignore[arg-type]

    result = cmd.execute({"args": SERVERMON_ARGS_STANDARD_DBONLY})

    assert cli.calls == [SERVERMON_ARGS_STANDARD_DBONLY]
    assert result == SP_OUTPUT_SERVERMON_OK
