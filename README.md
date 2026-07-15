# IBM Storage Protect MCP Server

The IBM Storage Protect Model Context Protocol (MCP) server enables natural language administration of IBM Storage Protect systems through AI-powered automation. Transform complex command-line operations into simple conversational interactions.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Quick Install (Recommended - Wheel Package)](#quick-install-recommended---wheel-package)
  - [Developer Install (From Source)](#developer-install-from-source)
- [Environment variables](#environment-variables)
- [Usage Examples](#usage-examples)
- [Reporting Issues and Feedback](#reporting-issues-and-feedback)
- [Contributing Code](#contributing-code)
- [Disclaimer](#disclaimer)

---

## Prerequisites

- IBM Storage Protect server
- Administrator credentials with appropriate permissions
- Access to the server instance user account (typically `tsminst1`)
- Python 3.10 or higher (Python 3.11 recommended)
- pip package manager

---

## Installation

### Quick Install (Recommended - Wheel Package)

The easiest way to install the IBM Storage Protect MCP server is using the pre-built wheel package. This method eliminates the need to clone the repository or build from source.

#### Linux/Unix Installation

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

**Step 7: Configure MCP Client**

Add to your MCP client configuration:
```json
{
  "mcpServers": {
    "sp-mcp-server": {
      "command": "sshpass",
      "args": [
        "-p",
        "your_root_password",
        "ssh",
        "-o",
        "StrictHostKeyChecking=no",
        "root@your-sp-server",
        "cd /opt/sp-mcp-server && source venv/bin/activate && python3 -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

**Installation complete!** The MCP server is ready to use.

#### Windows Installation

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

Follow the SSH setup instructions below for Windows-specific configuration.

---

### Developer Install (From Source)

For developers who want to contribute or customize the code, install from source:

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

For detailed build and distribution instructions, see [DISTRIBUTION.md](DISTRIBUTION.md).

---

#### SSH Setup for Windows (Remote Access)

If you need to access the Windows MCP server remotely from a Mac or Linux machine:

**Step 1: Generate SSH Key Pair**

On your local machine (Mac/Linux):
```bash
ssh-keygen -t rsa -b 4096 -f ~/.ssh/id_rsa_windows
```

**Step 2: Copy Public Key to Windows**

```bash
ssh-copy-id -i ~/.ssh/id_rsa_windows.pub SPuser@<windows-machine-ip>
```

Or manually append the public key content to `C:\Users\SPuser\.ssh\authorized_keys` on Windows.

**Step 3: Test SSH Connection**

```bash
ssh -i ~/.ssh/id_rsa_windows SPuser@<windows-machine-ip>
```

**Step 4: Configure MCP Client**

Add to your MCP client configuration:
```json
{
  "mcpServers": {
    "sp-mcp-server-windows": {
      "command": "ssh",
      "args": [
        "-i",
        "/Users/<your-username>/.ssh/id_rsa_windows",
        "SPuser@<windows-machine-ip>",
        "powershell",
        "-NoProfile",
        "-Command",
        "cd C:\\sp-mcp-server; .\\venv\\Scripts\\Activate.ps1; python -m sp_mcp_server.main --mode full --enable-servers system,operations,clients,policy,storage"
      ],
      "disabled": false,
      "alwaysAllow": []
    }
  }
}
```

---

## Environment variables 

#### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `SP_ADMIN_ID` | IBM Storage Protect administrator ID | `admin` |
| `SP_ADMIN_PASSWORD` | IBM Storage Protect administrator password | `password123` |

#### Optional Variables

| Variable | Description | Default | Example |
|----------|-------------|---------|---------|
| `TCPSERVERADDRESS` | Storage Protect server address | - | `sp-server.example.com` |
| `SP_SERVER_PORT` or `TCPPORT` | Server port number | `1500` | `1500` |
| `SP_DSMSERV_PATH` | Path to `dsmserv` executable | - | `/opt/tivoli/tsm/server/bin/dsmserv` |
| `SP_SERVER_INSTANCE_DIR` | Server instance directory | - | `/tsminst1` |
| `SP_SERVERMON_PATH` | Path to servermon executable | - | `/opt/tivoli/tsm/server/bin/servermon` |
| `SP_SERVERMON_XML_DIR` | Directory for servermon XML files | - | `/tmp/servermon` |
| `SP_INSTANCE_USER` | TSM instance user (required for `dsmserv` commands) | - | `tsmsvr01` |

### IBM Storage Protect instance user configuration

The `SP_INSTANCE_USER` environment variable is **critical** for running `dsmserv` commands. This variable specifies the IBM Storage Protect instance user account that the MCP server uses to execute `dsmserv` commands.

**Why it's required:**
Without the `SP_INSTANCE_USER` variable, `dsmserv` commands fail with library loading errors. You must run the `dsmserv` executable as the IBM Storage Protect instance user (typically `tsmsvr01`) to properly load required shared libraries. The MCP server wrapper uses the `su` command to switch to the specified instance user when executing `dsmserv` commands.

**Example error when `SP_INSTANCE_USER` is not set:**
```
/usr/bin/dsmserv: error while loading shared libraries: libdb2.so.1: cannot open shared object file: No such file or directory
```

### Configuration Example

```bash
# Required variables
export SP_ADMIN_ID=admin
export SP_ADMIN_PASSWORD=mypassword

# Optional variables
export TCPSERVERADDRESS=sp-server.example.com
export SP_SERVER_PORT=1500
export SP_DSMSERV_PATH=/opt/tivoli/tsm/server/bin/dsmserv
export SP_SERVER_INSTANCE_DIR=/tsminst1
export SP_SERVERMON_PATH=/opt/tivoli/tsm/server/bin/servermon
export SP_SERVERMON_XML_DIR=/tmp/servermon
export SP_INSTANCE_USER=tsmsvr01
```

---

## Usage Examples

### Basic Queries

```bash
# Query system status
"What is the database status?"

# List active clients
"Show me all active clients"

# Check failed operations
"Show me all failed operations from the last 24 hours"
```

### Configuration Tasks

```bash
# Create storage resources
"Create a device class named file_class of type file"

# Configure tiering
"Tell me the steps to tier data from container storage pool to cloud storage pool"
```

### Monitoring and Diagnostics

```bash
# System monitoring
"How many threads are running?"

# Capacity analysis
"Analyze current capacity utilization and forecast storage exhaustion"
```

---

## Reporting Issues and Feedback

For issues, questions, or feature requests, open an issue in the repository.

---

## Contributing Code

Contributions are welcome through Pull Requests. Complete the following steps to contribute:

1. Fork the repository and create a new branch for your feature or bug fix
2. Make your changes by following the existing code style and conventions
3. Test your changes thoroughly to ensure that they work as expected
4. Submit a pull request with a clear description of your changes
5. Sign the Developer's Certificate of Origin (DCO) by adding your name and email address to the `DCO.md` file in your pull request

**Note:** Submit your first Pull Request against the Developer's Certificate of Origin (DCO) located at `DCO.md` by using your name and email address.

---

## Disclaimer

This software is provided "as is" without any warranties of any kind, including, but not limited to, warranties related to installation, use, or performance. IBM is not responsible for any damage, charges, or data loss incurred with the use of this software. You are responsible for reviewing and testing any scripts you run thoroughly before you use them in any production environment. This content is subject to change without notice.

