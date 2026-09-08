# IBM Storage Protect MCP Server

The IBM Storage Protect Model Context Protocol (MCP) server exposes Storage Protect administration as structured tools for MCP-compatible AI clients. Describe an administrative task in natural language and the AI client invokes the appropriate `dsmadmc`-backed tool.

## What It Provides

- Monitoring and investigation of Storage Protect servers
- Client, storage, policy, and system administration
- Operational tools for protection, maintenance, rules, and diagnostics
- Unified and fine-grained MCP server deployments
- `stdio`/SSH and HTTP/SSE transport options
- Privilege-aware tool registration and audit correlation

## Setup and Usage

Use the end-user guides in [`docs/guides/`](docs/guides/) in this order:

1. **Plan** — [`planning-guide.md`](docs/guides/planning-guide.md)
   Choose a deployment topology, inventory Storage Protect servers, plan service accounts and SSH keys, and confirm prerequisites.
2. **Install** — [`install-guide.md`](docs/guides/install-guide.md)
   Set up the operating-system user, Python environment, package, credentials, TLS configuration, and Storage Protect integration.
3. **Configure** — [`configure-guide.md`](docs/guides/configure-guide.md)
   Configure the MCP client, transport, authentication, privilege scope, command approval, and multiple-server deployments.
4. **Use** — [`user-guide.md`](docs/guides/user-guide.md)
   Start and operate the server, select modules, address multiple servers, review audit records, and follow safe usage practices.
5. **Troubleshoot** — [`troubleshoot.md`](docs/guides/troubleshoot.md)
   Diagnose startup, credential, connection, transport, SSH, offline-command, and runtime problems.

The guide index at [`docs/guides/README.md`](docs/guides/README.md) provides the complete reading order and section summaries.

## Quick Start

After completing the guides, a manual `stdio` test can be started with:

```bash
cd /opt/sp-mcp-server
source .venv/bin/activate
python3 -m sp_mcp_server.main --mode full
```

For a safer monitoring deployment:

```bash
python3 -m sp_mcp_server.main --mode read-only
```

The MCP client normally starts the server for you. See [`configure-guide.md`](docs/guides/configure-guide.md) for client configuration examples and [`user-guide.md`](docs/guides/user-guide.md) for command-line options and server modules.

## Requirements

The detailed prerequisites and verification steps are maintained in [`planning-guide.md`](docs/guides/planning-guide.md) and [`install-guide.md`](docs/guides/install-guide.md). In general, you need:

- Python 3.10 or later
- A reachable IBM Storage Protect server
- The `dsmadmc` CLI on the MCP server host
- A dedicated non-root operating-system user
- Storage Protect administrator credentials with the required privilege

## Further Documentation

- [`docs/architecture/`](docs/architecture/) — system and module architecture
- [`docs/design/`](docs/design/) — security and design specifications
- [`docs/implement/`](docs/implement/) — implementation specifications
- [`docs/analysis/`](docs/analysis/) — design and security analysis
- [`docs/traceability/`](docs/traceability/) — requirements traceability, gap analysis, and independent audit report
- [`docs/example/sample-prompts.md`](docs/example/sample-prompts.md) — example administrator prompts
- [`docs/reference/`](docs/reference/) — product reference material

## Contributing

Contributions are welcome through pull requests. Follow the existing project conventions, test changes thoroughly, and sign the Developer's Certificate of Origin (DCO) where required.

## Disclaimer

This software is provided "as is" without warranties of any kind. Review and test all configuration and scripts before using them in production. IBM is not responsible for damage, charges, or data loss resulting from use of this software.
