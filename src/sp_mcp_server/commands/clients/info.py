from typing import Any, Dict
from ..base import BaseCommand

class QueryActiveSession(BaseCommand):
    @property
    def name(self) -> str:
        return "query_active_session"

    @property
    def description(self) -> str:
        return (
            "Display information about currently active administrative and node sessions.\n\n"
            "**Input Parameters**:\n"
            "- session_id (Optional): Specific session ID to query.\n\n"
            "**Output Parameters**:\n"
            "- Session ID: Unique identifier for the session.\n"
            "- Node Name: Name of the connected node/admin.\n"
            "- State: Current activity state (e.g., Run, Idle).\n"
            "- Bytes Sent/Recv: Amount of data transferred.\n"
            "- Wait Time: Time spent waiting for media."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "session_id": {"type": "string", "description": "Specific session ID to query."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY SESSION"
        if arguments.get("session_id"):
            cmd += f" {arguments['session_id']}"
        return self._execute_simple_query(cmd)

class QueryDataOccupancy(BaseCommand):
    @property
    def name(self) -> str:
        return "query_data_occupancy"

    @property
    def description(self) -> str:
        return (
            "Display statistics on where node data is stored and how much space it occupies.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Optional): Node name to filter.\n"
            "- backup_volume (Optional): Specific backup volume/filespace name.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The node.\n"
            "- Backup Volume Type: Specific file space or workload.\n"
            "- Storage Pool: Where the data resides.\n"
            "- Files: Number of files stored.\n"
            "- Physical Space: Space occupied (MB/GB)."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name to filter (maps to node_name)."},
                "backup_volume": {"type": "string", "description": "Specific backup volume/filespace name (maps to filespace_name)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY OCCUPANCY"
        if arguments.get("client_name"):
            cmd += f" {arguments['client_name']}"
        if arguments.get("backup_volume"):
            cmd += f" {arguments['backup_volume']}"
        return self._execute_simple_query(cmd)

class QueryAuditDataOccupancy(BaseCommand):
    @property
    def name(self) -> str:
        return "query_audit_data_occupancy"

    @property
    def description(self) -> str:
        return (
            "Query calculated total storage utilization for a node for audit purposes.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Optional): Node name to filter.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The node.\n"
            "- Backup Data: Space used by backup data.\n"
            "- Archive Data: Space used by archive data.\n"
            "- Total Space: Total space utilized."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name (maps to node_name)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY AUDITOCCUPANCY"
        if arguments.get("client_name"):
            cmd += f" {arguments['client_name']}"
        return self._execute_simple_query(cmd)

class QueryClientBackupVolume(BaseCommand):
    @property
    def name(self) -> str:
        return "query_client_backup_volume"

    @property
    def description(self) -> str:
        return (
            "Query information about node backup volumes (File Spaces). A backup volume represents a logical partition of data managed for a node (e.g., C: drive, /home, System State).\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Optional): Node name.\n"
            "- backup_volume (Optional): Backup volume/filespace name.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The node.\n"
            "- Backup Volume (File Space): The specific volume or mount point.\n"
            "- Capacity: Total size of the volume on the client.\n"
            "- Pct Utilized: Percentage used on the client."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name (maps to node_name)."},
                "backup_volume": {"type": "string", "description": "Backup volume name (maps to filespace_name)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY FILESPACE"
        if arguments.get("client_name"):
            cmd += f" {arguments['client_name']}"
        if arguments.get("backup_volume"):
            cmd += f" {arguments['backup_volume']}"
        return self._execute_simple_query(cmd)

class QueryVirtualMountPoint(BaseCommand):
    @property
    def name(self) -> str:
        return "query_virtual_mount_point"

    @property
    def description(self) -> str:
        return (
            "Query virtual mount point mappings for nodes, which map local paths to virtual filespaces.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Optional): Node name.\n"
            "- virtual_path (Optional): Virtual mount point name.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The node.\n"
            "- Virtual Mount Point: Name of the virtual filespace.\n"
            "- Local Path: The physical path mapped."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name."},
                "virtual_path": {"type": "string", "description": "Virtual mount point name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY VIRTUALFSMAPPING"
        if arguments.get("client_name"):
            cmd += f" {arguments['client_name']}"
        if arguments.get("virtual_path"):
            cmd += f" {arguments['virtual_path']}"
        return self._execute_simple_query(cmd)

class QueryClientDataPlacement(BaseCommand):
    @property
    def name(self) -> str:
        return "query_client_data_placement"

    @property
    def description(self) -> str:
        return (
            "Query distribution of node data across storage containers and volumes.\n\n"
            "**Input Parameters**:\n"
            "- node_name (Required*): Client node name(s). Wildcards and comma-separated lists supported. Required if collocgroup not specified.\n"
            "- collocgroup (Required*): Collocation group name. Required if node_name not specified. Cannot be used with node_name.\n"
            "- stgpool (Optional): Sequential storage pool name to query. Wildcards supported.\n"
            "- volume (Optional): Volume name containing the data. Wildcards supported.\n"
            "- filespace (Optional): Filespace name on the client node. Only valid with node_name.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The node.\n"
            "- Storage Pool: The container.\n"
            "- Volume Name: The specific volume."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {
                    "type": "string",
                    "description": "Client node name(s). Wildcards and comma-separated lists supported. Required if collocgroup not specified."
                },
                "collocgroup": {
                    "type": "string",
                    "description": "Collocation group name. Required if node_name not specified. Cannot be used with node_name."
                },
                "stgpool": {
                    "type": "string",
                    "description": "Sequential storage pool name to query. Wildcards supported. Default: all sequential-access pools."
                },
                "volume": {
                    "type": "string",
                    "description": "Volume name containing the data. Wildcards supported."
                },
                "filespace": {
                    "type": "string",
                    "description": "Filespace name on the client node. Only valid with node_name."
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        if not arguments.get("node_name") and not arguments.get("collocgroup"):
            return "Error: Either node_name or collocgroup must be specified."
        cmd = "QUERY NODEDATA"
        if arguments.get("node_name"):
            cmd += f" {arguments['node_name']}"
        if arguments.get("collocgroup"):
            cmd += f" COLLOCGroup={arguments['collocgroup']}"
        if arguments.get("stgpool"):
            cmd += f" STGpool={arguments['stgpool']}"
        if arguments.get("volume"):
            cmd += f" VOLume={arguments['volume']}"
        if arguments.get("filespace"):
            cmd += f" FIlespace={arguments['filespace']}"
        return self._execute_simple_query(cmd)
