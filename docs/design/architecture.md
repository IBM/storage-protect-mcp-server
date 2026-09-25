# IBM Storage Protect MCP Server - Architecture

## Overview

The IBM Storage Protect MCP Server is a Model Context Protocol (MCP) implementation that enables AI-powered natural language administration of IBM Storage Protect systems. The architecture follows a modular, extensible design that separates concerns between protocol handling, command execution, and IBM Storage Protect CLI interaction.

## Architecture Principles

1. **Modularity**: Commands are organized into logical functional groups (clients, storage, policies, system, operations)
2. **Extensibility**: New commands can be added by implementing base command classes
3. **Separation of Concerns**: Clear boundaries between MCP protocol handling, command logic, and CLI execution
4. **Type Safety**: Comprehensive JSON schema validation for all tool inputs
5. **Security**: Support for read-only and full operation modes with granular permission control
6. **Logging**: Comprehensive logging with file rotation for debugging and audit trails

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client (AI Agent)                     │
│                    (Claude, GPT, or other LLM)                   │
└────────────────────────────┬────────────────────────────────────┘
                             │ MCP Protocol (stdio)
                             │
┌────────────────────────────▼────────────────────────────────────┐
│                      MCP Server Layer                            │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              main.py (Entry Point)                       │   │
│  │  - Argument parsing (--enable-servers, --mode)           │   │
│  │  - Server group selection                                │   │
│  │  - Async runtime initialization                          │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │         mcp_factory.py (Server Factory)                  │   │
│  │  - MCP Server instantiation                              │   │
│  │  - Tool registration and discovery                       │   │
│  │  - Request routing (list_tools, call_tool)               │   │
│  │  - Mode filtering (read-only vs full)                    │   │
│  │  - Logging configuration                                 │   │
│  └────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────┼──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                   Command Layer                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │         server_groups.py (Command Organization)          │   │
│  │  - ISP_CLIENTS_CORE, ISP_CLIENTS_CONFIG                 │   │
│  │  - ISP_STORAGE_POOLS, ISP_STORAGE_HARDWARE, ...         │   │
│  │  - ISP_POLICIES_LIFECYCLE, ISP_POLICIES_MANAGEMENT      │   │
│  │  - ISP_SYSTEM_ADMIN, ISP_SYSTEM_CONFIG                  │   │
│  │  - ISP_OPS_PROTECTION, ISP_OPS_MAINTENANCE, ...         │   │
│  └────────────────────────┬─────────────────────────────────┘   │
│                           │                                      │
│  ┌────────────────────────▼─────────────────────────────────┐   │
│  │           commands/ (Command Implementations)            │   │
│  │  ┌──────────────────────────────────────────────────┐    │   │
│  │  │  base.py (Base Command Classes)                  │    │   │
│  │  │  - BaseCommand (online dsmadmc commands)         │    │   │
│  │  │  - BaseOfflineCommand (offline dsmserv commands) │    │   │
│  │  │  - BaseServermonCommand (servermon commands)     │    │   │
│  │  └──────────────────────────────────────────────────┘    │   │
│  │  ┌──────────────────────────────────────────────────┐    │   │
│  │  │  clients/ - Client management commands           │    │   │
│  │  │  storage/ - Storage management commands          │    │   │
│  │  │  policies/ - Policy management commands          │    │   │
│  │  │  system/ - System administration commands        │    │   │
│  │  │  operations/ - Operational commands              │    │   │
│  │  │  offline.py - Offline database commands          │    │   │
│  │  │  servermon.py - Server monitoring commands       │    │   │
│  │  └──────────────────────────────────────────────────┘    │   │
│  └────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────┼──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│                    CLI Wrapper Layer                             │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │              cli_wrapper.py                              │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  DsmAdmcWrapper                                    │  │   │
│  │  │  - Online administrative commands                  │  │   │
│  │  │  - Session management                              │  │   │
│  │  │  - Output parsing                                  │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  DsmServWrapper                                    │  │   │
│  │  │  - Offline database commands                       │  │   │
│  │  │  - Instance user switching (su)                    │  │   │
│  │  │  - Library path management                         │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  │  ┌────────────────────────────────────────────────────┐  │   │
│  │  │  ServermonWrapper                                  │  │   │
│  │  │  - Server monitoring commands                      │  │   │
│  │  │  - XML output parsing                              │  │   │
│  │  └────────────────────────────────────────────────────┘  │   │
│  └────────────────────────┬─────────────────────────────────┘   │
└───────────────────────────┼──────────────────────────────────────┘
                            │
┌───────────────────────────▼──────────────────────────────────────┐
│              IBM Storage Protect Server                          │
│  - dsmadmc (Administrative CLI)                                  │
│  - dsmserv (Server executable)                                   │
│  - servermon (Monitoring utility)                                │
└──────────────────────────────────────────────────────────────────┘
```

## Core Components

### 1. Entry Point (`main.py`)

**Responsibilities:**
- Parse command-line arguments (`--enable-servers`, `--mode`)
- Load environment variables from `.env` file
- Select and enable server modules based on configuration
- Initialize the async runtime
- Start the MCP server

**Key Features:**
- Modular server selection (system, operations, clients, policy, storage)
- Operation mode control (full vs read-only)
- Graceful error handling and logging

### 2. MCP Factory (`mcp_factory.py`)

**Responsibilities:**
- Create and configure the MCP Server instance
- Instantiate command classes with appropriate CLI wrappers
- Register tools with the MCP protocol
- Route tool calls to command implementations
- Filter commands based on operation mode
- Configure comprehensive logging

**Key Features:**
- Dynamic tool discovery and registration
- Mode-based command filtering
- Async tool execution with thread pooling
- Rotating file logs with console output
- Error handling and reporting

### 3. Server Groups (`server_groups.py`)

**Responsibilities:**
- Organize commands into logical functional groups
- Define server module compositions
- Enable selective feature activation

**Server Groups:**

| Group | Module | Command Count | Focus Area |
|-------|--------|---------------|------------|
| **Clients** | `ISP_CLIENTS_CORE` | ~17 | Node lifecycle, registration, deletion |
| | `ISP_CLIENTS_CONFIG` | ~10 | Client options, schedules, associations |
| **Storage** | `ISP_STORAGE_POOLS` | ~13 | Storage pools, volumes, containers |
| | `ISP_STORAGE_HARDWARE` | ~14 | Libraries, drives, paths |
| | `ISP_STORAGE_DEVICE` | ~9 | Device classes, data movers |
| **Policies** | `ISP_POLICIES_LIFECYCLE` | ~10 | Policy domains, sets, activation |
| | `ISP_POLICIES_MANAGEMENT` | ~12 | Management classes, copy groups, schedules |
| **System** | `ISP_SYSTEM_ADMIN` | ~12 | Administrators, permissions, licensing |
| | `ISP_SYSTEM_CONFIG` | ~13 | Server configuration, scripts, connections |
| **Operations** | `ISP_OPS_PROTECTION` | ~10 | DB backup, replication, disaster recovery |
| | `ISP_OPS_MAINTENANCE` | ~12 | Data movement, cleanup, jobs |
| | `ISP_OPS_RULES` | ~13 | Automation rules, alerts, triggers |

### 4. Command Layer (`commands/`)

**Base Classes:**

#### `BaseCommand` (Online Commands)
- Uses `DsmAdmcWrapper` for online administrative commands
- Requires active server connection
- Supports session management
- Examples: RegisterNode, DefineStoragePool, QueryClient

#### `BaseOfflineCommand` (Offline Commands)
- Uses `DsmServWrapper` for offline database operations
- Requires instance user privileges
- No active server connection needed
- Examples: QueryOfflineDBSpace, QueryOfflineLog

#### `BaseServermonCommand` (Monitoring Commands)
- Uses `ServermonWrapper` for server monitoring
- Parses XML output
- Real-time server metrics
- Examples: RunServerMon

**Command Structure:**
```python
class ExampleCommand(BaseCommand):
    name = "command_name"
    description = "Command description"
    tool_type = "read-only"  # or "full"
    
    args_schema = {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "..."},
            # ...
        },
        "required": ["param1"]
    }
    
    def execute(self, args: dict) -> str:
        # Command implementation
        result = self.cli.run_command("COMMAND", args)
        return self.format_output(result)
```

### 5. CLI Wrapper Layer (`cli_wrapper.py`)

#### `DsmAdmcWrapper`
**Purpose:** Execute online administrative commands via `dsmadmc`

**Features:**
- Automatic session management
- Command formatting and escaping
- Output parsing and error handling
- Credential management from environment variables

**Usage:**
```python
wrapper = DsmAdmcWrapper(config)
result = wrapper.run_command("QUERY NODE", {"node_name": "CLIENT1"})
```

#### `DsmServWrapper`
**Purpose:** Execute offline database commands via `dsmserv`

**Features:**
- Instance user switching (via `su`)
- Library path management (LD_LIBRARY_PATH)
- Offline database access
- Error detection and reporting

**Usage:**
```python
wrapper = DsmServWrapper(config)
result = wrapper.run_command("DISPLAY DBSPACE", {})
```

#### `ServermonWrapper`
**Purpose:** Execute server monitoring commands via `servermon`

**Features:**
- XML output parsing
- Real-time metrics collection
- Thread and process monitoring
- Performance data extraction

**Usage:**
```python
wrapper = ServermonWrapper(config)
result = wrapper.run_command("servermon status", {})
```

### 6. Configuration Management (`config.py`)

**Responsibilities:**
- Load environment variables
- Validate required configuration
- Provide configuration to CLI wrappers

**Required Variables:**
- `SP_ADMIN_ID`: Administrator username
- `SP_ADMIN_PASSWORD`: Administrator password

**Optional Variables:**
- `TCPSERVERADDRESS`: Server hostname/IP
- `SP_SERVER_PORT` / `TCPPORT`: Server port (default: 1500)
- `SP_DSMSERV_PATH`: Path to dsmserv executable
- `SP_SERVER_INSTANCE_DIR`: Server instance directory
- `SP_SERVERMON_PATH`: Path to servermon executable
- `SP_SERVERMON_XML_DIR`: Directory for servermon XML output
- `SP_INSTANCE_USER`: TSM instance user (required for dsmserv commands)

## Command Execution Flow

```
1. MCP Client sends tool call request
   ↓
2. MCP Server receives request via stdio
   ↓
3. mcp_factory routes to appropriate command
   ↓
4. Command validates input against JSON schema
   ↓
5. Command calls CLI wrapper with formatted arguments
   ↓
6. CLI wrapper executes IBM SP command
   ↓
7. CLI wrapper parses output and handles errors
   ↓
8. Command formats output for MCP protocol
   ↓
9. MCP Server returns response to client
```

## Operation Modes

### Full Mode (Default)
- All commands available (read-only + destructive)
- Create, update, delete operations enabled
- Suitable for administrative automation

### Read-Only Mode
- Only query and informational commands available
- No state-changing operations
- Suitable for monitoring and reporting

**Mode Filtering:**
Commands are tagged with `tool_type`:
- `"read-only"`: Query and informational commands
- `"full"`: State-changing commands (create, update, delete)

The factory filters commands based on the selected mode.

## Extension Points

### Adding New Commands

1. **Create Command Class:**
```python
# In commands/clients/new_command.py
from ..base import BaseCommand

class NewCommand(BaseCommand):
    name = "new_command"
    description = "Description of the command"
    tool_type = "read-only"  # or "full"
    
    args_schema = {
        "type": "object",
        "properties": {
            "param": {"type": "string"}
        },
        "required": ["param"]
    }
    
    def execute(self, args: dict) -> str:
        result = self.cli.run_command("SP_COMMAND", args)
        return self.format_output(result)
```

2. **Register in Server Group:**
```python
# In server_groups.py
from sp_mcp_server.commands.clients import NewCommand

ISP_CLIENTS_CORE = [
    # ... existing commands
    NewCommand,
]
```

3. **Test the Command:**
```bash
python -m sp_mcp_server.main --enable-servers clients
```

### Adding New Server Groups

1. **Define Group in `server_groups.py`:**
```python
ISP_NEW_GROUP = [
    Command1,
    Command2,
    # ...
]
```

2. **Register in `main.py`:**
```python
SERVER_GROUPS = {
    # ... existing groups
    "new_group": ISP_NEW_GROUP,
}
```

3. **Enable via CLI:**
```bash
python -m sp_mcp_server.main --enable-servers new_group
```

## Security Considerations

1. **Credential Management:**
   - Credentials stored in environment variables
   - `.env` file should have restricted permissions (600)
   - Never log credentials

2. **Command Validation:**
   - All inputs validated against JSON schemas
   - SQL injection prevention via parameterized commands
   - Command escaping in CLI wrappers

3. **Access Control:**
   - Mode-based operation restrictions
   - IBM SP native permission system enforced
   - Audit logging enabled

4. **Network Security:**
   - SSH tunneling recommended for remote access
   - TLS/SSL for IBM SP connections
   - Firewall rules for port 1500

## Logging and Monitoring

### Log Configuration
- **Location:** `/var/log/ibm-sp-mcp-server/mcp-server.log` (fallback: `/tmp/ibm-sp-mcp-server/`)
- **Rotation:** 10MB max file size, 5 backup files
- **Levels:** DEBUG (file), INFO (console)
- **Format:** Timestamp, logger name, level, file:line, message

### Log Categories
- **Server Lifecycle:** Startup, shutdown, configuration
- **Tool Execution:** Tool calls, arguments, results
- **CLI Operations:** Command execution, output parsing
- **Errors:** Exceptions, validation failures, CLI errors

### Monitoring Points
- Tool execution time
- CLI command success/failure rates
- Error patterns and frequencies
- Resource utilization (via servermon)

## Performance Considerations

1. **Async Execution:**
   - Tool calls executed in thread pool
   - Non-blocking I/O for MCP protocol
   - Concurrent command execution support

2. **CLI Optimization:**
   - Command batching where possible
   - Output parsing optimization
   - Connection pooling for dsmadmc

3. **Resource Management:**
   - Proper cleanup of CLI processes
   - Memory-efficient output handling
   - Log rotation to prevent disk exhaustion

## Testing Strategy

1. **Unit Tests:**
   - Command validation logic
   - Output parsing functions
   - Schema validation

2. **Integration Tests:**
   - CLI wrapper functionality
   - End-to-end command execution
   - Error handling scenarios

3. **System Tests:**
   - Full server operation
   - Multi-command workflows
   - Mode switching

## Deployment Architecture

### Standalone Deployment
```
┌─────────────────────────────────────┐
│   IBM Storage Protect Server        │
│   - MCP Server (local)               │
│   - dsmadmc, dsmserv, servermon     │
└─────────────────────────────────────┘
```

### Remote Deployment (SSH)
```
┌──────────────────┐         SSH         ┌─────────────────────────┐
│   MCP Client     │ ◄──────────────────► │  IBM SP Server          │
│   (Mac/Linux)    │                      │  - MCP Server           │
└──────────────────┘                      │  - IBM SP Components    │
                                          └─────────────────────────┘
```

### Multi-Server Deployment
```
┌──────────────────┐
│   MCP Client     │
└────────┬─────────┘
         │
    ┌────┴────┬────────┬────────┐
    │         │        │        │
┌───▼───┐ ┌──▼───┐ ┌──▼───┐ ┌──▼───┐
│ SP-1  │ │ SP-2 │ │ SP-3 │ │ SP-4 │
│ MCP   │ │ MCP  │ │ MCP  │ │ MCP  │
└───────┘ └──────┘ └──────┘ └──────┘
```

## Future Enhancements

1. **Command Caching:**
   - Cache query results for frequently accessed data
   - Invalidation strategies
   - TTL-based expiration

2. **Batch Operations:**
   - Multi-command transactions
   - Rollback support
   - Atomic operations

3. **Advanced Monitoring:**
   - Real-time metrics streaming
   - Alerting integration
   - Performance analytics

4. **Enhanced Security:**
   - OAuth/OIDC integration
   - Role-based access control (RBAC)
   - Audit trail enhancements

5. **High Availability:**
   - Failover support
   - Load balancing
   - State synchronization

## Conclusion

The IBM Storage Protect MCP Server architecture provides a robust, extensible foundation for AI-powered administration of IBM Storage Protect systems. The modular design enables easy addition of new commands, flexible deployment options, and comprehensive operational control while maintaining security and performance standards.
