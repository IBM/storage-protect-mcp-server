# Quick Installation Guide - Wheel Package

This is a quick reference for installing the IBM Storage Protect MCP Server using the pre-built wheel package.

## Download Wheel

Get the latest wheel file:
- **Version**: 1.0.0
- **Filename**: `ibm_sp_mcp_server-1.0.0-py3-none-any.whl`
- **Size**: ~101KB

Download from:
- GitHub Releases: https://github.com/IBM/ibm-storage-protect-mcp-server/releases
- Or build locally: `./build_wheel.sh`

## Quick Install (Linux/Unix)

```bash
# 1. Install Python 3.10+
sudo dnf install python3.11 python3.11-pip -y  # RHEL/CentOS
# or
sudo apt install python3.11 python3.11-venv -y  # Ubuntu/Debian

# 2. Create directory and virtual environment
sudo mkdir -p /opt/sp-mcp-server
cd /opt/sp-mcp-server
python3.11 -m venv venv
source venv/bin/activate

# 3. Install wheel
pip install ibm_sp_mcp_server-1.0.0-py3-none-any.whl

# 4. Verify installation
sp-mcp-server --help
```

## Quick Install (Windows)

```powershell
# 1. Install Python 3.10+ from python.org

# 2. Create directory and virtual environment
mkdir C:\sp-mcp-server
cd C:\sp-mcp-server
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1

# 3. Install wheel
pip install ibm_sp_mcp_server-1.0.0-py3-none-any.whl

# 4. Verify installation
sp-mcp-server --help
```

## Configuration

Create `.env` file:

```bash
SP_ADMIN_ID=tsmadmin
SP_ADMIN_PASSWORD=your_password
SP_INSTANCE_USER=tsminst1
SP_SERVERMON_XML_DIR=/home/tsminst1/tsminst1/srvmon
SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin
SP_SERVER_INSTANCE_DIR=/home/tsminst1
SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon/servermon
```

## MCP Client Configuration

Add to your MCP client (Bob, Claude, Cursor):

```json
{
  "mcpServers": {
    "sp-mcp-server": {
      "command": "ssh",
      "args": [
        "root@your-sp-server",
        "cd /opt/sp-mcp-server && source venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ]
    }
  }
}
```

## Upgrade

```bash
pip install --upgrade ibm_sp_mcp_server-1.1.0-py3-none-any.whl
```

## Documentation

- Full installation guide: [README.md](README.md)
- Distribution details: [DISTRIBUTION.md](DISTRIBUTION.md)
- GitHub: https://github.com/IBM/ibm-storage-protect-mcp-server
