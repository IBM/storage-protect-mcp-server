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

## Sample Prompts

For example prompts and longer task-oriented prompt patterns, see [`docs/example/sample-prompts.md`](docs/example/sample-prompts.md).

## Reporting Issues and Feedback

For issues, questions, or feature requests, open an issue in the repository.

## Contributing Code

Contributions are welcome through Pull Requests. Complete the following steps to contribute:

1. Fork the repository and create a new branch for your feature or bug fix.
2. Make your changes by following the existing code style and conventions.
3. Test your changes thoroughly to ensure that they work as expected.
4. Submit a pull request with a clear description of your changes.
5. Sign the Developer's Certificate of Origin (DCO) by adding your name and email address to the `DCO.md` file in your pull request.

> **Note:** Submit your first Pull Request against the Developer's Certificate of Origin (DCO) located at `DCO.md` by using your name and email address.

## Disclaimer

This software is provided "as is" without any warranties of any kind, including, but not limited to, warranties related to installation, use, or performance. IBM is not responsible for any damage, charges, or data loss incurred with the use of this software. You are responsible for reviewing and testing any scripts you run thoroughly before you use them in any production environment. This content is subject to change without notice.
