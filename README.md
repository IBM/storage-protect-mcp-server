# IBM Storage Protect MCP Server

The IBM Storage Protect Model Context Protocol (MCP) server exposes Storage Protect administration as structured tools for MCP-compatible AI clients. Describe an administrative task in natural language and the AI client invokes the appropriate `dsmadmc`-backed tool.

## What It Provides

- Monitoring and investigation of Storage Protect servers
- Client, storage, policy, and system administration
- Operational tools for protection, maintenance, rules, and diagnostics
- Unified and fine-grained MCP server deployments
- `stdio`/SSH and HTTP/SSE transport options
- Privilege-aware tool registration and audit correlation

## Requirements

- Python 3.10 or later
- A reachable IBM Storage Protect server
- The `dsmadmc` CLI on the MCP server host
- A dedicated non-root operating-system user
- Storage Protect administrator credentials with the required privilege

Full prerequisite details and verification steps are in [`docs/guides/planning-guide.md`](docs/guides/planning-guide.md) and [`docs/guides/install-guide.md`](docs/guides/install-guide.md).

## Install & Configure

Follow the guides in [`docs/guides/`](docs/guides/) in order. Each guide links to the next.

### 1. Plan — [`docs/guides/planning-guide.md`](docs/guides/planning-guide.md)

Choose a deployment topology (co-located on each SP server host, or centralised on a single control host), inventory your Storage Protect servers, plan service accounts and SSH keys, and confirm system prerequisites.

### 2. Install — [`docs/guides/install-guide.md`](docs/guides/install-guide.md)

Set up the OS user and working directory, create a Python virtual environment, install the package and its dependencies, write the `.env` credential file with 0600 permissions, configure TLS certificates for HTTP transport, and verify the Storage Protect connection.

Key steps at a glance:

```bash
# Create the virtual environment and install
python3.11 -m venv .venv
source .venv/bin/activate
pip install -e ".[sse]"          # or: pip install -r requirements-sse.txt

# Write credentials (owner-read-only)
install -m 600 /dev/null .env
echo "SP_ADMIN_ID=mcp-svc-system"     >> .env
echo "SP_ADMIN_PASSWORD=<password>"   >> .env
echo "SP_SERVER_ADDRESS=your-sp-host" >> .env
echo "SP_SERVER_PORT=1500"            >> .env
```

Full topology-specific instructions (co-located vs centralised, SSH key deployment, TLS setup) are in [`install-guide.md`](docs/guides/install-guide.md).

### 3. Configure — [`docs/guides/configure-guide.md`](docs/guides/configure-guide.md)

Register the MCP server in your AI client (Claude Desktop, VS Code Copilot, or similar). Choose a transport:

| Transport | When to use |
|-----------|-------------|
| `stdio` over SSH | Single-client, local, or Claude Desktop deployments |
| `http` with OIDC | Enterprise, multi-client, or REST gateway deployments |

Example `stdio` + SSH entry for Claude Desktop (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "sp-admin": {
      "command": "ssh",
      "args": [
        "-i", "~/.ssh/id_ed25519_sp_mcp",
        "-o", "StrictHostKeyChecking=yes",
        "mcp-runner@your-sp-server",
        "/opt/sp-mcp-server/.venv/bin/python3",
        "-m", "sp_mcp_server.main",
        "--mode", "full"
      ]
    }
  }
}
```

Authentication modes, privilege scoping, multi-server configurations, and HTTP/OIDC setup are covered in [`configure-guide.md`](docs/guides/configure-guide.md).

## Usage

Full usage reference is in [`docs/guides/user-guide.md`](docs/guides/user-guide.md). The sections below summarise the most common starting points.

### Starting the server manually

The MCP client normally launches the server for you via the configured command. For testing or offline use, start it directly:

```bash
cd /opt/sp-mcp-server
source .venv/bin/activate

# Full administrative access
python3 -m sp_mcp_server.main --mode full

# Monitoring / read-only (safest for first run)
python3 -m sp_mcp_server.main --mode read-only
```

### Specialised server modules

Instead of the unified `main` server you can launch a focused module that exposes only the tools for one administrative domain:

| Module | Command | Scope |
|--------|---------|-------|
| Client core | `mcp-server-clients-core` | Node and group management |
| Client config | `mcp-server-clients-config` | Node options and settings |
| Storage pools | `mcp-server-storage-pools` | Storage pool and volume management |
| Storage hardware | `mcp-server-storage-hardware` | Library and drive management |
| Storage device | `mcp-server-storage-device` | Device class and data-mover configuration |
| Policies lifecycle | `mcp-server-policies-lifecycle` | Policy sets and activation |
| Policies management | `mcp-server-policies-management` | Management classes and copy groups |
| System admin | `mcp-server-system-admin` | Administrators and licensing |
| System config | `mcp-server-system-config` | Server options, schedules, and monitoring |
| Operations | `mcp-server-ops` | Status, sessions, and activity log |
| Ops protection | `mcp-server-ops-protection` | Backup rules and recovery |
| Ops maintenance | `mcp-server-ops-maintenance` | Database, log, and media maintenance |
| Ops rules | `mcp-server-ops-rules` | Administrative schedules and rules |

### Privilege tiers

The server narrows the registered tool set to match the IBM SP privilege class of the active account:

| Privilege class | Tools available |
|-----------------|----------------|
| System | All tools — full administrative scope |
| Policy | Policy management + all read-only tools |
| Storage | Storage management + all read-only tools |
| Operator | Operations (sessions, media, jobs) + read-only tools |
| Any-admin (no class) | Read-only `QUERY` tools only |

Use `--mode read-only` to restrict to read-only tools regardless of privilege class.

### Authentication modes

| Mode | `SP_MCP_AUTH_MODE` value | Best for |
|------|--------------------------|----------|
| Static tiered service accounts (default) | `service_account` | Automated pipelines, daemons, single-tenant bots |
| Dynamic challenge-response | `dynamic` | Interactive chat (Claude Desktop) — users authenticate per session |

See [`user-guide.md`](docs/guides/user-guide.md) for session lifecycle, audit records, and safe usage practices.

### Troubleshooting

Startup errors, credential failures, connection problems, SSH issues, and runtime diagnostics are covered in [`docs/guides/troubleshoot.md`](docs/guides/troubleshoot.md).

## Documentation

| Path | Contents |
|------|----------|
| [`docs/guides/`](docs/guides/) | End-user guides: planning, install, configure, use, troubleshoot |
| [`docs/architecture/`](docs/architecture/) | System and module architecture |
| [`docs/design/`](docs/design/) | Security and design specifications |
| [`docs/implement/`](docs/implement/) | Implementation specifications |
| [`docs/analysis/`](docs/analysis/) | Design and security analysis |
| [`docs/traceability/`](docs/traceability/) | Requirements traceability, gap analysis, and independent audit report |
| [`docs/reference/`](docs/reference/) | Product reference material |
| [`docs/example/sample-prompts.md`](docs/example/sample-prompts.md) | Example administrator prompts and task patterns |

## Contributing

Contributions are welcome through Pull Requests. To contribute:

1. Fork the repository and create a new branch for your feature or bug fix.
2. Follow the existing code style and conventions.
3. Test your changes thoroughly before submitting.
4. Submit a pull request with a clear description of your changes.
5. Sign the Developer's Certificate of Origin (DCO) by adding your name and email address to `DCO.md` in your pull request.

For issues, questions, or feature requests, open an issue in the repository.

## Disclaimer

This software is provided "as is" without any warranties of any kind, including, but not limited to, warranties related to installation, use, or performance. IBM is not responsible for any damage, charges, or data loss incurred with the use of this software. You are responsible for reviewing and testing any scripts you run thoroughly before you use them in any production environment. This content is subject to change without notice.
