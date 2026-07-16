from sp_mcp_server.config import ServerConfig, load_config


def test_load_config_defaults(monkeypatch):
    monkeypatch.delenv("TCPSERVERADDRESS", raising=False)
    monkeypatch.delenv("SP_SERVER_PORT", raising=False)
    monkeypatch.delenv("TCPPORT", raising=False)
    monkeypatch.setenv("SP_ADMIN_ID", "admin")
    monkeypatch.setenv("SP_ADMIN_PASSWORD", "password")
    monkeypatch.delenv("SP_DSMSERV_PATH", raising=False)
    monkeypatch.delenv("SP_SERVER_INSTANCE_DIR", raising=False)
    monkeypatch.delenv("SP_SERVERMON_PATH", raising=False)
    monkeypatch.delenv("SP_SERVERMON_XML_DIR", raising=False)
    monkeypatch.delenv("SP_INSTANCE_USER", raising=False)

    config = load_config()

    assert config.server_address is None
    assert config.server_port == "1500"
    assert config.admin_id == "admin"
    assert config.admin_password == "password"
    assert config.dsmserv_path is None
    assert config.server_instance_dir is None
    assert config.servermon_path is None
    assert config.servermon_xml_dir is None
    assert config.instance_user is None


def test_load_config_full(monkeypatch):
    monkeypatch.setenv("TCPSERVERADDRESS", "prod.server.com")
    monkeypatch.setenv("SP_SERVER_PORT", "1600")
    monkeypatch.setenv("SP_ADMIN_ID", "superuser")
    monkeypatch.setenv("SP_ADMIN_PASSWORD", "secret")
    monkeypatch.setenv("SP_DSMSERV_PATH", "/opt/tivoli/tsm/server/bin/dsmserv")
    monkeypatch.setenv("SP_SERVER_INSTANCE_DIR", "/tsm/instance")
    monkeypatch.setenv("SP_SERVERMON_PATH", "/opt/tivoli/tsm/server/bin/servermon")
    monkeypatch.setenv("SP_SERVERMON_XML_DIR", "/tsm/srvmon")
    monkeypatch.setenv("SP_INSTANCE_USER", "tsminst1")

    config = load_config()

    assert config.server_address == "prod.server.com"
    assert config.server_port == "1600"
    assert config.admin_id == "superuser"
    assert config.admin_password == "secret"
    assert config.dsmserv_path == "/opt/tivoli/tsm/server/bin/dsmserv"
    assert config.server_instance_dir == "/tsm/instance"
    assert config.servermon_path == "/opt/tivoli/tsm/server/bin/servermon"
    assert config.servermon_xml_dir == "/tsm/srvmon"
    assert config.instance_user == "tsminst1"


def test_load_config_prefers_sp_server_port_over_tcpport(monkeypatch):
    monkeypatch.setenv("SP_SERVER_PORT", "1700")
    monkeypatch.setenv("TCPPORT", "1800")
    monkeypatch.setenv("SP_ADMIN_ID", "admin")
    monkeypatch.setenv("SP_ADMIN_PASSWORD", "password")

    config = load_config()

    assert config.server_port == "1700"


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
