# Configuration Guide

This guide contains MCP client configuration examples for connecting to the IBM Storage Protect MCP Server from Linux and Windows environments.

## Linux MCP Client Configuration

Add the following to your MCP client configuration:

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

## Windows MCP Client Configuration

### SSH Setup for Windows Remote Access

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

Add the following to your MCP client configuration:

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

## Related Documentation

- Installation steps: [`install-guide.md`](install-guide.md)
- User guidance: [`user-guide.md`](user-guide.md)
- Main project overview: [`../../README.md`](../../README.md)
