# Installation Guide

This guide contains the installation procedures moved from `README.md`.

## Quick Install (Recommended - Wheel Package)

The easiest way to install the IBM Storage Protect MCP server is using the pre-built wheel package. This method eliminates the need to clone the repository or build from source.

### Linux/Unix Installation

**Step 1: Install Python 3.10 or Higher**

For RHEL/CentOS/Rocky Linux:
```bash
sudo dnf install python3.11 python3.11-pip python3.11-devel -y
python3.11 --version
```

For Ubuntu/Debian:
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y
python3.11 --version
```

**Step 2: Create Installation Directory**

```bash
sudo mkdir -p /opt/sp-mcp-server
cd /opt/sp-mcp-server
```

**Step 3: Create Virtual Environment**

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

**Step 4: Install from Wheel**

Download the wheel file and install:
```bash
# Option A: Install from local wheel file
pip install ibm_sp_mcp_server-1.0.0-py3-none-any.whl

# Option B: Install from URL (when available)
pip install https://github.com/IBM/ibm-storage-protect-mcp-server/releases/download/v1.0.0/ibm_sp_mcp_server-1.0.0-py3-none-any.whl

# Option C: Install from PyPI (when published)
pip install ibm-sp-mcp-server
```

**Step 5: Verify Installation**

```bash
# Check installed package
pip list | grep ibm-sp

# Verify commands are available
which sp-mcp-server
sp-mcp-server --help
```

**Step 6: Configure Environment Variables**

Create a `.env` file:
```bash
cat > /opt/sp-mcp-server/.env << 'EOF'
SP_ADMIN_ID=tsmadmin
SP_ADMIN_PASSWORD=your_password_here
SP_INSTANCE_USER=tsminst1
SP_SERVERMON_XML_DIR=/home/tsminst1/tsminst1/srvmon
SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin
SP_SERVER_INSTANCE_DIR=/home/tsminst1
SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon/servermon
EOF

chmod 600 /opt/sp-mcp-server/.env
```

## Windows Installation

**Step 1: Install Python 3.10 or Higher**

Download and install Python 3.11 from [python.org](https://www.python.org/downloads/).

**Step 2: Create Installation Directory**

```powershell
mkdir C:\sp-mcp-server
cd C:\sp-mcp-server
```

**Step 3: Create Virtual Environment**

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
```

**Step 4: Install from Wheel**

```powershell
pip install ibm_sp_mcp_server-1.0.0-py3-none-any.whl
```

**Step 5: Configure Environment Variables**

Create `.env` file:
```powershell
@"
SP_ADMIN_ID=tsmadmin
SP_ADMIN_PASSWORD=your_password_here
SP_INSTANCE_USER=tsminst1
SP_SERVERMON_XML_DIR=C:\TSM\srvmon
"@ | Out-File -FilePath .env -Encoding UTF8
```

**Step 6: Configure SSH and MCP Client**

Follow the SSH setup instructions in `README.md` for Windows-specific remote configuration.

## Developer Install (From Source)

For developers who want to contribute or customize the code, install from source.

**Step 1: Clone the Repository**

```bash
git clone https://github.com/IBM/ibm-storage-protect-mcp-server
cd ibm-storage-protect-mcp-server
git checkout dev
```

**Step 2: Create Virtual Environment**

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

**Step 3: Install in Development Mode**

```bash
pip install -e .
```

**Step 4: Verify Installation**

```bash
pip list | grep -E "mcp|ibm-sp"
which sp-mcp-server
```

**Step 5: Configure Environment Variables**

Follow the same `.env` configuration steps as the Quick Install method above.

For detailed build and distribution instructions, see `build/distribution.md`.