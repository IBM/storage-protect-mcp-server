# Security Advisory: Plaintext Credentials in the MCP Server Log

## Summary

Earlier releases of the IBM Storage Protect MCP Server could write the
arguments of password-bearing tool calls to the persistent log file
(`mcp-server.log`) in clear text, and created that file readable by other local
accounts.

* The server configured the **root logger at DEBUG** and wrote everything to the
  rotating log file. The MCP SDK's HTTP/SSE transport logs each raw POST body
  (`Received JSON: b'{...}'`) at DEBUG **before** the request is authorized
  or redacted, so a request that was later *denied* was still
  recorded. The SDK's low-level server also logs parsed messages at DEBUG, which
  affects the stdio transport as well.
* Log files and directories were created with the process umask (typically
  `0644` / `0755`). If `/var/log/ibm-sp-mcp-server` could not be created, the
  server silently fell back to the predictable path `/tmp/ibm-sp-mcp-server/`.

A local user, or any role that can read the log (log collectors, support
bundles, backups), could therefore recover passwords supplied by another
administrator or automation identity.

## Affected

All releases up to and including **v1.1.0**, and the `main` branch before the
fix, when any password-bearing tool is invoked. Tools that accept a password
argument:

| Area | Tools |
| :--- | :--- |
| Administrators | `define_admin`, `update_user` |
| Dynamic authentication | `authenticate_session` |
| Server-to-server | `define_server`, `update_server`, `define_connection`, `update_connection` |
| Data movers | `define_data_mover`, `update_data_mover` |
| Clients | `register_node`, `update_node` |

OIDC bearer tokens travel in HTTP headers, not the request body, and were not
part of the logged body. Command-line secrets passed to `dsmadmc` were already
excluded from the log by earlier releases.

## Fixed behavior

* The root logger now defaults to `INFO` (`SP_MCP_LOG_LEVEL`). The `mcp`,
  `httpx`, `httpcore` and `starlette` loggers are pinned to `WARNING`, so SDK
  request bodies are never persisted, even if an operator requests `DEBUG`.
* A redaction filter masks `password`, `secret`, `token`, `api_key` and
  `Authorization`/`Bearer` values as a defense-in-depth backstop.
* Log files are created `0600`; log directories created by the server are
  `0700`. Existing files and rotated backups are tightened on startup.
* The `/tmp` fallback is now a per-user directory
  (`<tmpdir>/ibm-sp-mcp-server-<uid>`) that must be a real directory owned by
  the service user. If it fails validation, file logging is disabled and only
  stderr is used.
* Offline (`dsmserv`) and `servermon` execution no longer log argument values.
* On startup, the server warns if it finds log files from an earlier version.

## Required actions after upgrading

Upgrading stops new exposure but **does not remove credentials already written
to disk**.

1. **Find and delete existing logs.** Include rotated backups and the old
   fallback location:

   ```bash
   # default location, or $SP_MCP_LOG_DIR
   sudo find /var/log/ibm-sp-mcp-server -name 'mcp-server.log*' -type f -delete
   # old predictable fallback path
   sudo rm -rf /tmp/ibm-sp-mcp-server
   ```

   Stop the service first so no handle remains open on a deleted file.
2. **Remove copies outside the host.** Check log shippers and collectors
   (rsyslog, filebeat, SIEM indices), backups and snapshots of the log
   directory, and any support bundles or tickets that attached the log.
3. **Rotate every password that may have been sent through the server**,
   starting with the highest privilege: administrator accounts created or
   updated with the tools above, the service accounts used by the MCP server,
   inter-server and connection passwords, data-mover passwords, node passwords,
   and the password of any user who signed in through `authenticate_session`.
4. **Verify nothing is left** (adjust the path as needed):

   ```bash
   sudo grep -rliE 'password' /var/log/ibm-sp-mcp-server /tmp/ibm-sp-mcp-server* 2>/dev/null
   ```
5. **Provision the log directory explicitly** so the secure location is used
   instead of the fallback:

   ```bash
   sudo install -d -m 0750 -o mcp-runner -g mcp-runner /var/log/ibm-sp-mcp-server
   ```

If you cannot upgrade immediately, restrict the log directory to the service
account (`chmod 700`), and avoid password-bearing tool calls over any transport
until the fix is deployed.
