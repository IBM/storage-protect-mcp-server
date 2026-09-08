# Guides

End-user guides for the IBM Storage Protect MCP Server. Read these in order when setting up for the first time.

---

## Reading Order

| Step | Document | When to read |
|------|----------|--------------|
| **1** | [`planning-guide.md`](planning-guide.md) | **Before anything else** — Choose your deployment topology (co-located or centralised), inventory your SP servers, plan service accounts, SSH keys, and tool scope, and confirm prerequisites |
| **2** | [`install-guide.md`](install-guide.md) | **After planning** — OS user setup, Python virtual environment, package install, `.env` files, SP service account provisioning, `dsm.sys` TLS configuration, and installation verification |
| **3** | [`configure-guide.md`](configure-guide.md) | **After installing** — MCP client configuration for stdio/SSH and HTTP/OIDC transports, privilege-aware tool registration, command approval, and multi-server setup for both topologies |
| **4** | [`user-guide.md`](user-guide.md) | **Before first use** — Privilege tiers, tool access control, `--mode` flag, managing multiple SP servers from prompts, audit trail, and safe usage guidance |
| **Reference** | [`troubleshoot.md`](troubleshoot.md) | **When something goes wrong** — Error markers, startup failures, credential errors, offline command failures, Python import errors, and multi-server deployment issues |

---

## Guide Summaries

### `planning-guide.md`

Covers all decisions and checks that must be made **before** installing anything:

- **Topology choice** — Co-located (Topology A: one MCP process per SP server host) vs Centralised (Topology B: all processes on one control host); topology diagrams, comparison table, pros/cons, and offline tools limitation
- **SP server inventory** — Hostname, admin port, `SERVERNAME` label, MCP entry name, and tool scope per server
- **Prerequisites verification** — Python, `dsmadmc`, TCP 1500 access, and OS access per topology
- **Service account planning** — Five per-privilege accounts per SP server; MFA exemption policy
- **`dsm.sys` SERVERNAME planning** — Unique labels per SP server to prevent password stash collisions
- **SSH key planning** — One key per SP host (Topology A) or one key to the control host (Topology B)
- **MCP client entry naming** — The entry name becomes the AI agent routing key in prompts
- **Tool scope planning** — `--mode` and `--enable-servers` per SP server entry
- **Pre-installation sign-off checklist**

### `install-guide.md`

Covers topology-specific installation steps — run after completing `planning-guide.md`:

- **OS user setup** — `mcp-runner` non-root account on each SP host (A) or once on the control host (B)
- **Python environment** — RHEL/Ubuntu install, virtual environment creation; shared venv for Topology B
- **Package installation** — Wheel or source install; verification
- **`.env` configuration** — One per SP host (A) or one per SP server subdirectory on the control host (B); full environment variable reference with topology column
- **SP service account provisioning** — `REGISTER ADMIN`, `GRANT AUTHORITY`, `SESSIONSECURITY=STRICT` for all five privilege tiers on each SP server
- **`dsm.sys` TLS configuration** — Single stanza (A) or multi-stanza file (B); password stash population per account per SP server
- **sudoers rule** — Topology A only; enables offline `dsmserv` / `servermon` tools
- **Installation verification** — Per-host (A) or per-subdirectory (B) smoke test
- **Post-install checklists** — Separate for Topology A and Topology B

### `configure-guide.md`

Covers MCP client configuration — run after completing `install-guide.md`:

- **stdio over SSH** (Part 1) — Ed25519 key generation and deployment, `StrictHostKeyChecking=yes`, MCP client JSON snippets for Linux/macOS and Windows, `sshd_config` hardening
- **HTTP/OIDC transport** (Part 2) — TLS certificate setup, OIDC token scope, bearer token authentication, HTTP transport verification
- **Privilege-aware tool registration** (Part 3) — How `--mode` and service account privilege combine to gate tool visibility
- **Command approval** (Part 4) — `SET COMMANDAPPROVAL ON`, pending command queue, two-person integrity
- **Multiple SP servers** (Part 5) — Step-by-step setup for both topologies:
  - **Topology A** — Per-host SSH keys, per-host MCP client entries, per-host `.env` layout, provisioning checklist
  - **Topology B** — Single control-host SSH key, `cd`-based `.env` isolation, centralised MCP client config, security controls table, provisioning checklist
  - **Common** — Tool scoping per entry, prompt addressing, security controls summary

### `user-guide.md`

Covers day-to-day operation after the server is installed and configured:

- **What the MCP server does** — Use case categories: monitoring, investigation, client management, storage, policy, system administration, offline diagnostics
- **Privilege tiers** — The five SP privilege classes, which tools each tier exposes, and how `--mode` overlays on top
- **Managing multiple SP servers** — One-process-to-one-SP-server model, prompt-based server addressing, `isp_server_name` parameter caveat
- **Starting the server** — Manual start commands for all modes; `--mode`, `--enable-servers`, `--transport`, `--port` arguments
- **Server modules** — What each `--enable-servers` module covers and its typical account
- **Password protection** — `.env` permissions, keyring-first resolution, password stash mode, silent execution for credential-bearing commands
- **Audit trail** — `DEFINE SCRATCHPADENTRY MCP_AUDIT` correlation IDs, per-server ACTLOG distribution
- **Command approval workflow** — `approve_pending_command`, `reject_pending_command`, `withdraw_pending_command`
- **Example prompts** — Monitoring, investigation, administration, storage, approval, and multi-server targeting
- **Safe usage guidance** — Read-only first, review before confirming, narrowest account, per-server SSH keys
- **Basic validation checklist** — Single-host and multi-server SSH variants
- **Log file** — Log path, key log markers table, per-host log note for multi-server deployments

### `troubleshoot.md`

A quick-reference error guide keyed by log marker, covering startup failures through runtime issues:

| Log marker | Issue | Section |
|---|---|---|
| `SECURITY [CRED-3]` | `.env` has insecure permissions — `chmod 600 .env` | §1 |
| `SECURITY [RG-1]` | Production bypass guard — `SP_MCP_SKIP_SECURITY_CHECKS=1` blocked | §2 |
| `SECURITY [NET-1]` | Session security check failed — `SESSIONSECURITY` not `STRICT` | §3 |
| `SECURITY [RG-5]` | HTTP transport TLS not configured | §4 |
| `SECURITY [POL-3]` | Account lockout advisory — `INVALIDPWLIMIT` is 0 | §5 |
| `SECURITY [POL-4 / RG-4]` | Audit write failed — ACTLOG record missing | §6 |
| `dsmadmc executable not found` | `dsmadmc` not in `PATH` on the MCP server host | §7 |
| `No credential available` | Missing `.env` entry for the required privilege tier | §8 |
| `ACC-2: Skipping tool` | Tool excluded — insufficient service account privilege | §9 |
| `sudo:` in stderr | Offline command sudoers rule missing or wrong path | §10 |
| `ImportError` / `ModuleNotFoundError` | Python import failure — wrong venv or missing package | §11 |
| Password stash issues | Stash not populated or `SERVERNAME` collision | §12 |
| Connection failures | SP server unreachable on TCP 1500 | §13 |
| SSH connection issues | Key not deployed, wrong key, or host key mismatch | §14 |
| Multi-server issues | One process fails, stash collision, SSH key used for wrong host | §15 |

---

## Cross-References

- Sample prompts: [`../example/sample-prompts.md`](../example/sample-prompts.md)
- Architecture overview: [`../architecture/architecture.md`](../architecture/architecture.md)
- Security controls: [`../analysis/security-design-analysis.md`](../analysis/security-design-analysis.md)
- Security design — Identity & Credentials: [`../design/security-identity-credentials.md`](../design/security-identity-credentials.md)
- Security design — Network: [`../design/security-network.md`](../design/security-network.md)
- Security design — Access: [`../design/security-access.md`](../design/security-access.md)
