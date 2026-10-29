from sp_mcp_server.config import ServerConfig, load_config

from tests.fixtures import (
    make_server_config,
    SP_ALT_SERVER_ADDRESS,
    SP_ALT_SERVER_PORT,
    SP_SERVER_PORT,
    SP_INSTANCE_DIR_ALT,
    SERVERMON_XML_DIR_ALT,
    ADMIN_ID,
    ADMIN_PASSWORD,
    ALT_ADMIN_ID,
    ALT_ADMIN_PASSWORD,
    SP_INSTANCE_USER,
    DSMSERV_PATH_FULL,
    SERVERMON_PATH_FULL,
)


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("TCPSERVERADDRESS", raising=False)
    monkeypatch.delenv("SP_SERVER_PORT", raising=False)
    monkeypatch.delenv("TCPPORT", raising=False)
    monkeypatch.setenv("SP_ADMIN_ID", ADMIN_ID)
    monkeypatch.setenv("SP_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.delenv("SP_DSMSERV_PATH", raising=False)
    monkeypatch.delenv("SP_SERVER_INSTANCE_DIR", raising=False)
    monkeypatch.delenv("SP_SERVERMON_PATH", raising=False)
    monkeypatch.delenv("SP_SERVERMON_XML_DIR", raising=False)
    monkeypatch.delenv("SP_INSTANCE_USER", raising=False)

    config = load_config()

    assert config.server_address is None
    assert config.server_port == SP_SERVER_PORT
    assert config.admin_id == ADMIN_ID
    assert config.admin_password == ADMIN_PASSWORD
    assert config.dsmserv_path is None
    assert config.server_instance_dir is None
    assert config.servermon_path is None
    assert config.servermon_xml_dir is None
    assert config.instance_user is None


def test_load_config_full(monkeypatch):
    monkeypatch.setenv("TCPSERVERADDRESS", SP_ALT_SERVER_ADDRESS)
    monkeypatch.setenv("SP_SERVER_PORT", SP_ALT_SERVER_PORT)
    monkeypatch.setenv("SP_ADMIN_ID", ALT_ADMIN_ID)
    monkeypatch.setenv("SP_ADMIN_PASSWORD", ALT_ADMIN_PASSWORD)
    monkeypatch.setenv("SP_DSMSERV_PATH", DSMSERV_PATH_FULL)
    monkeypatch.setenv("SP_SERVER_INSTANCE_DIR", SP_INSTANCE_DIR_ALT)
    monkeypatch.setenv("SP_SERVERMON_PATH", SERVERMON_PATH_FULL)
    monkeypatch.setenv("SP_SERVERMON_XML_DIR", SERVERMON_XML_DIR_ALT)
    monkeypatch.setenv("SP_INSTANCE_USER", SP_INSTANCE_USER)

    config = load_config()

    assert config.server_address == SP_ALT_SERVER_ADDRESS
    assert config.server_port == SP_ALT_SERVER_PORT
    assert config.admin_id == ALT_ADMIN_ID
    assert config.admin_password == ALT_ADMIN_PASSWORD
    assert config.dsmserv_path == DSMSERV_PATH_FULL
    assert config.server_instance_dir == SP_INSTANCE_DIR_ALT
    assert config.servermon_path == SERVERMON_PATH_FULL
    assert config.servermon_xml_dir == SERVERMON_XML_DIR_ALT
    assert config.instance_user == SP_INSTANCE_USER


def test_load_config_prefers_sp_server_port_over_tcpport(monkeypatch):
    SP_PORT_PRIORITY = "1700"
    TCPPORT_VALUE = "1800"
    monkeypatch.setenv("SP_SERVER_PORT", SP_PORT_PRIORITY)
    monkeypatch.setenv("TCPPORT", TCPPORT_VALUE)
    monkeypatch.setenv("SP_ADMIN_ID", ADMIN_ID)
    monkeypatch.setenv("SP_ADMIN_PASSWORD", ADMIN_PASSWORD)

    config = load_config()

    assert config.server_port == SP_PORT_PRIORITY


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
