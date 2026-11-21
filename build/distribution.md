# IBM Storage Protect MCP Server - Distribution Guide

This guide explains how to build and distribute the IBM Storage Protect MCP Server as a wheel package for simplified installation.

## Table of Contents

- [Building the Wheel Package](#building-the-wheel-package)
- [Installing from Wheel](#installing-from-wheel)
  - [Linux/Unix Installation](#linuxunix-installation)
  - [Windows Installation](#windows-installation)
- [Version Management](#version-management)
- [Distribution Methods](#distribution-methods)

---

## Building the Wheel Package

### Prerequisites

- Python 3.10 or higher
- pip package manager
- Git (for cloning the repository)

### Build Steps

1. **Clone the repository** (for maintainers/developers):
   ```bash
   git clone https://github.com/IBM/ibm-storage-protect-mcp-server
   cd ibm-storage-protect-mcp-server
   git checkout dev  # or main branch
   ```

2. **Run the build script**:
   ```bash
   chmod +x build/build_wheel.sh
   ./build/build_wheel.sh
   ```

   The script will:
   - Verify Python version (3.10+)
   - Clean previous build artifacts
   - Install/upgrade build tools
   - Generate the wheel file in the `dist/` directory

3. **Locate the wheel file**:
   ```bash
   ls -lh dist/
   # Output: ibm_sp_mcp_server-1.0.0-py3-none-any.whl
   ```

### Manual Build (Alternative)

If you prefer to build manually:

```bash
# Install build tools
pip install --upgrade pip build wheel setuptools

# Clean previous builds
rm -rf build/ dist/ *.egg-info src/*.egg-info

# Build the wheel
python3 -m build --wheel
```

---

## Installing from Wheel

### Linux/Unix Installation

#### Step 1: Install Python 3.10 or Higher

**RHEL/CentOS/Rocky Linux:**
```bash
sudo dnf install python3.11 python3.11-pip python3.11-devel -y
python3.11 --version
```

**Ubuntu/Debian:**
```bash
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev -y
python3.11 --version
```

#### Step 2: Install Additional Build Tools (if needed)

**RHEL/CentOS/Rocky Linux:**
```bash
sudo dnf groupinstall "Development Tools" -y
sudo dnf install gcc gcc-c++ make openssl-devel bzip2-devel libffi-devel -y
```

**Ubuntu/Debian:**
```bash
sudo apt install build-essential gcc g++ make libssl-dev libbz2-dev libffi-dev -y
```

#### Step 3: Create Installation Directory

```bash
sudo mkdir -p /opt/sp-mcp-server
cd /opt/sp-mcp-server
```

#### Step 4: Create Virtual Environment

```bash
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
```

#### Step 5: Install from Wheel

**Option A: Install from local wheel file**
```bash
# Copy wheel file to server
scp ibm_sp_mcp_server-1.0.0-py3-none-any.whl user@server:/opt/sp-mcp-server/

# Install
pip install ibm_sp_mcp_server-1.0.0-py3-none-any.whl
```

**Option B: Install from remote URL**
```bash
pip install https://example.com/path/to/ibm_sp_mcp_server-1.0.0-py3-none-any.whl
```

**Option C: Install from PyPI (when published)**
```bash
pip install ibm-sp-mcp-server
```

#### Step 6: Verify Installation

```bash
# Check installed package
pip list | grep ibm-sp

# Verify commands are available
which sp-mcp-server
which mcp-server-clients-core
which mcp-server-system-admin

# Test help output
sp-mcp-server --help
```

#### Step 7: Configure Environment Variables

Create a `.env` file in `/opt/sp-mcp-server`:

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

# Secure the file
chmod 600 /opt/sp-mcp-server/.env
```

#### Step 8: Configure MCP Client

Add to your MCP client configuration (e.g., Bob, Claude, Cursor):

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

---

### Windows Installation

#### Step 1: Install Python 3.10 or Higher

Download and install Python 3.11 from [python.org](https://www.python.org/downloads/).

Verify installation:
```powershell
python --version
pip --version
```

#### Step 2: Create Installation Directory

```powershell
mkdir C:\sp-mcp-server
cd C:\sp-mcp-server
```

#### Step 3: Create Virtual Environment

```powershell
py -3.11 -m venv venv
.\venv\Scripts\Activate.ps1
```

#### Step 4: Install from Wheel

**Option A: Install from local wheel file**
```powershell
# Copy wheel file to Windows machine
# Then install
pip install ibm_sp_mcp_server-1.0.0-py3-none-any.whl
```

**Option B: Install from remote URL**
```powershell
pip install https://example.com/path/to/ibm_sp_mcp_server-1.0.0-py3-none-any.whl
```

**Option C: Install from PyPI (when published)**
```powershell
pip install ibm-sp-mcp-server
```

#### Step 5: Verify Installation

```powershell
# Check installed package
pip list | Select-String "ibm-sp"

# Verify commands
where sp-mcp-server
where mcp-server-clients-core

# Test help output
sp-mcp-server --help
```

#### Step 6: Configure Environment Variables

Create `.env` file in `C:\sp-mcp-server`:

```powershell
@"
SP_ADMIN_ID=tsmadmin
SP_ADMIN_PASSWORD=your_password_here
SP_INSTANCE_USER=tsminst1
SP_SERVERMON_XML_DIR=C:\TSM\srvmon
"@ | Out-File -FilePath .env -Encoding UTF8
```

#### Step 7: Configure SSH and MCP Client

Follow the SSH setup instructions in the main README.md for Windows-specific configuration.

---

## Version Management

### Semantic Versioning

The project follows [Semantic Versioning](https://semver.org/):

- **MAJOR.MINOR.PATCH** (e.g., 1.0.0)
  - **MAJOR**: Incompatible API changes
  - **MINOR**: New functionality (backward compatible)
  - **PATCH**: Bug fixes (backward compatible)

### Updating Version

Edit `pyproject.toml`:

```toml
[project]
name = "ibm-sp-mcp-server"
version = "1.0.0"  # Update this line
```

### Version History

- **1.0.0** - Initial stable release with wheel distribution support
- **0.1.0** - Development version

---

## Distribution Methods

### 1. Direct File Distribution

Share the wheel file directly with users:

```bash
# Build the wheel
./build/build_wheel.sh

# Share the file
scp dist/ibm_sp_mcp_server-1.0.0-py3-none-any.whl user@target:/tmp/
```

### 2. Internal Package Repository

Host on an internal PyPI server:

```bash
# Upload to internal PyPI
twine upload --repository-url https://pypi.internal.company.com dist/*.whl
```

### 3. GitHub Releases

Attach wheel files to GitHub releases:

1. Create a new release on GitHub
2. Upload the wheel file as a release asset
3. Users can download and install:
   ```bash
   pip install https://github.com/IBM/ibm-storage-protect-mcp-server/releases/download/v1.0.0/ibm_sp_mcp_server-1.0.0-py3-none-any.whl
   ```

### 4. PyPI (Public Python Package Index)

For public distribution:

```bash
# Install twine
pip install twine

# Upload to PyPI
twine upload dist/*

# Users can then install with:
pip install ibm-sp-mcp-server
```

---

## Upgrading

To upgrade to a newer version:

```bash
# Activate virtual environment
source venv/bin/activate  # Linux/Unix
# or
.\venv\Scripts\Activate.ps1  # Windows

# Upgrade from wheel file
pip install --upgrade ibm_sp_mcp_server-1.1.0-py3-none-any.whl

# Or from PyPI
pip install --upgrade ibm-sp-mcp-server
```

---

## Troubleshooting

### Build Issues

**Problem**: Build fails with "No module named 'build'"
```bash
# Solution: Install build tools
pip install --upgrade build wheel setuptools
```

**Problem**: Permission denied when running build script
```bash
# Solution: Make script executable
chmod +x build/build_wheel.sh
```

### Installation Issues

**Problem**: "ERROR: Could not find a version that satisfies the requirement"
```bash
# Solution: Ensure Python 3.10+ is being used
python3 --version
```

**Problem**: Command not found after installation
```bash
# Solution: Ensure virtual environment is activated
source venv/bin/activate  # Linux/Unix
.\venv\Scripts\Activate.ps1  # Windows
```

---

## Support

For issues, questions, or feature requests:
- Open an issue on GitHub: https://github.com/IBM/ibm-storage-protect-mcp-server/issues
- Refer to the main README.md for detailed usage instructions

---

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
