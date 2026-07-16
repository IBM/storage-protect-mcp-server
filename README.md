# IBM Storage Protect MCP Server

The IBM Storage Protect Model Context Protocol (MCP) server enables natural language administration of IBM Storage Protect systems through AI-powered automation. Transform complex command-line operations into simple conversational interactions.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [Installation Guide Reference](#installation-guide-reference)
- [Configure MCP Client](#configure-mcp-client)
- [Environment variables](#environment-variables)
- [Sample Prompts](#sample-prompts)
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

### Installation Guide Reference

The detailed installation procedures are in [`docs/guides/install-guide.md`](docs/guides/install-guide.md), which includes:

- Quick Install (Recommended - Wheel Package)
- Windows Installation

---

## Configure MCP Client

MCP client configuration examples for both Linux and Windows are in [`docs/guides/configure-guide.md`](docs/guides/configure-guide.md).

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

```text
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

## Sample Prompts

For example prompts and longer task-oriented prompt patterns, see [`docs/example/sample-prompts.md`](docs/example/sample-prompts.md).

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