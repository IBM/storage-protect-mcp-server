from typing import Any, Dict
from ..base import BaseCommand

class DefineVolume(BaseCommand):
    @property
    def name(self) -> str:
        return "define_volume"

    @property
    def description(self) -> str:
        return (
            "- Description: Defines a **Storage Unit** (known as a **Volume** in SP) within a Storage Pool. Represents a specific disk, file, or tape.\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): The name of the parent Storage Pool.\n"
            "- volume_name (Required): Unique identifier/path for the volume.\n"
            "- access (Optional): Availability mode (e.g., 'READWRITE', 'READONLY').\n"
            "- formatsize (Optional): Size in MB to allocate for the new volume file. Required when the volume file does not already exist on disk (DISK/FILE device class pools). Max: 8000000 MB.\n"
            "- numberofvolumes (Optional): Number of volumes to create in one step (1-256). If > 1, formatsize is also required.\n"
            "- wait (Optional): YES = foreground operation, NO = background (default when formatsize is specified).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the volume was defined."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name."},
                "volume_name": {"type": "string", "description": "Volume name."},
                "access": {
                    "type": "string",
                    "enum": ["READWRITE", "READONLY", "UNAVAILABLE", "DESTROYED", "OFFSITE"],
                    "description": "Access mode."
                },
                "formatsize": {
                    "type": "integer",
                    "description": "Size in MB to allocate for the new volume file. Required when the volume file does not already exist on disk (DISK/FILE device class pools). Max: 8000000 MB."
                },
                "numberofvolumes": {
                    "type": "integer",
                    "description": "Number of volumes to create in one step (1-256). If > 1, formatsize is also required."
                },
                "wait": {
                    "type": "string",
                    "enum": ["YES", "NO"],
                    "description": "YES = foreground operation, NO = background (default when formatsize is specified)."
                }
            },
            "required": ["pool_name", "volume_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE VOLUME {arguments['pool_name']} {arguments['volume_name']}"
        if arguments.get("access"):
            cmd += f" ACCESS={arguments['access']}"
        if arguments.get("formatsize"):
            cmd += f" FORMATSIZE={arguments['formatsize']}"
        if arguments.get("numberofvolumes"):
            cmd += f" NUMBEROFVOLUMES={arguments['numberofvolumes']}"
        if arguments.get("wait"):
            cmd += f" WAIT={arguments['wait']}"
        return self._execute_simple_query(cmd)

class UpdateVolume(BaseCommand):
    @property
    def name(self) -> str:
        return "update_volume"
    @property
    def description(self) -> str:
        return (
            "- Description: Updates an existing **Storage Volume**. Can modify its access mode.\n"
            "**Input Parameters**:\n"
            "- volume_name (Required): The name of the volume to update.\n"
            "- access (Optional): The new access mode (READWRITE, READONLY, UNAVAILABLE, DESTROYED, OFFSITE).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the volume was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "volume_name": {"type": "string", "description": "Volume name."},
                "access": {"type": "string", "enum": ["READWRITE", "READONLY", "UNAVAILABLE", "DESTROYED", "OFFSITE"], "description": "Access mode."}
            },
            "required": ["volume_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE VOLUME {arguments['volume_name']}"
        if arguments.get("access"): cmd += f" ACCESS={arguments['access']}"
        return self._execute_simple_query(cmd)

class UpdateVolumeHistory(BaseCommand):
    @property
    def name(self) -> str:
        return "update_volume_history"
    @property
    def description(self) -> str:
        return (
            "- Description: Updates **Volume History** information. Can change the physical location of a volume.\n"
            "**Input Parameters**:\n"
            "- volume_name (Required): The name of the volume.\n"
            "- location (Optional): The physical location description for the volume.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the volume history was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "volume_name": {"type": "string", "description": "Volume name."},
                "location": {"type": "string", "description": "Location description."}
            },
            "required": ["volume_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE VOLHISTORY {arguments['volume_name']}"
        if arguments.get("location"): cmd += f" LOCATION=\"{arguments['location']}\""
        return self._execute_simple_query(cmd)

class DeleteVolume(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_volume"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Storage Volume**.\n"
            "**Input Parameters**:\n"
            "- volume_name (Required): The name of the volume to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the volume was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "volume_name": {"type": "string", "description": "Volume name."},
                "discard_data": {"type": "string", "enum": ["YES", "NO"], "description": "Discard data?"}
            },
            "required": ["volume_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DELETE VOLUME {arguments['volume_name']}"
        if arguments.get("discard_data"): cmd += f" DISCARDDATA={arguments['discard_data']}"
        return self._execute_simple_query(cmd)

class QueryMediaVolume(BaseCommand):
    @property
    def name(self) -> str:
        return "query_media_volume"

    @property
    def description(self) -> str:
        return (
            "- Description: Queries **Storage Units** (Volumes) within a target. Returns capacity, status, and physical location info.\n"
            "**Input Parameters**:\n"
            "- volume_name (Optional): Specific volume name.\n"
            "- container_name (Optional): Filter volumes by Storage Pool.\n"
            "- status (Optional): Filter by status (e.g., 'FILLING', 'FULL', 'UNAVAILABLE').\n"
            "**Output Parameters**:\n"
            "- Volume Name: Unique path/identifier.\n"
            "- Storage Pool Name: Parent Storage Pool.\n"
            "- Estimated Capacity: Total size.\n"
            "- Pct Util: Percentage filled.\n"
            "- Status: Operational status."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "volume_name": {"type": "string", "description": "Specific volume name to query."},
                "container_name": {"type": "string", "description": "Filter by storage container name (maps to pool_name)."},
                "status": {"type": "string", "description": "Filter by volume status (e.g., ONLINE, DAMAGED)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY VOLUME"
        if arguments.get("volume_name"):
            cmd += f" {arguments['volume_name']}"
        
        if arguments.get("container_name"):
            cmd += f" STGPOOL={arguments['container_name']}"
        if arguments.get("status"):
            cmd += f" STATUS={arguments['status']}"
            
        return self._execute_simple_query(cmd)

class QueryVolumeHistory(BaseCommand):
    @property
    def name(self) -> str:
        return "query_volume_history"

    @property
    def description(self) -> str:
        return (
            "- Description: Display historical records of sequential volume usage (e.g., Database Backups).\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- type (Optional): Type of history to query (e.g., DBBACKUP, EXPORT, RPFILE).\n"
            "**Output Parameters**:\n"
            "- Date/Time: When the volume was written.\n"
            "- Volume Name: The name of the volume.\n"
            "- Type: Type of data (e.g., BACKUPFULL, RPFILE)."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                 "type": {"type": "string", "description": "Type of history to query (e.g., DBBACKUP, EXPORT, RPFILE)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY VOLHISTORY"
        if arguments.get("type"):
            cmd += f" TYPE={arguments['type']}"
        return self._execute_simple_query(cmd)

class QuerySequentialMedia(BaseCommand):
    @property
    def name(self) -> str:
        return "query_sequential_media"

    @property
    def description(self) -> str:
        return (
            "- Description: Query sequential-access media associated with a storage pool.\n"
            "**Input Parameters**:\n"
            "- stgpool_name (Required): Sequential-access storage pool name. Wildcards supported.\n"
            "- volume_name (Optional): Volume name filter. Wildcards supported.\n"
            "- days (Optional): Days elapsed since last read/write (0-9999, default 0).\n"
            "- where_status (Optional): Filter by volume status: FULl, FILling, EMPty. Comma-separated.\n"
            "- where_access (Optional): Filter by access mode: READWrite, READOnly.\n"
            "- where_state (Optional): Filter by mount state: All, MOUNTABLEInlib, MOUNTABLENotinlib.\n"
            "- format (Optional): Output format: Standard, Detailed.\n"
            "**Output Parameters**:\n"
            "- Volume Name: The media volume.\n"
            "- State: Mountable or not.\n"
            "- Location: Current location of the volume."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "stgpool_name": {"type": "string", "description": "Sequential-access storage pool name (required). Wildcards supported."},
                "volume_name": {"type": "string", "description": "Volume name filter (optional). Wildcards supported."},
                "days": {"type": "integer", "description": "Days elapsed since last read/write (optional, 0–9999, default 0)."},
                "where_status": {"type": "string", "description": "Filter by volume status (optional): FULl, FILling, EMPty. Comma-separated."},
                "where_access": {"type": "string", "description": "Filter by access mode (optional): READWrite, READOnly.", "enum": ["READWrite", "READOnly"]},
                "where_state": {"type": "string", "description": "Filter by mount state (optional).", "enum": ["All", "MOUNTABLEInlib", "MOUNTABLENotinlib"]},
                "format": {"type": "string", "description": "Output format (optional).", "enum": ["Standard", "Detailed"]}
            },
            "required": ["stgpool_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY MEDIA"
        if arguments.get("volume_name"):
            cmd += f" {arguments['volume_name']}"
        cmd += f" STGPOOL={arguments['stgpool_name']}"
        if arguments.get("days") is not None:
            cmd += f" Days={arguments['days']}"
        if arguments.get("where_status"):
            cmd += f" WHERESTATUs={arguments['where_status']}"
        if arguments.get("where_access"):
            cmd += f" WHEREACCess={arguments['where_access']}"
        if arguments.get("where_state"):
            cmd += f" WHEREState={arguments['where_state']}"
        if arguments.get("format"):
            cmd += f" Format={arguments['format']}"
        return self._execute_simple_query(cmd)

class QueryMountedVolumes(BaseCommand):
    @property
    def name(self) -> str:
        return "query_mounted_volumes"

    @property
    def description(self) -> str:
        return (
            "- Description: Display information on currently mounted sequential access volumes.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "**Output Parameters**:\n"
            "- Volume Name: The mounted volume.\n"
            "- Drive Name: The drive it is mounted in.\n"
            "- Library Name: The library containing the drive."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY MOUNT")

class QueryRecoveryMedia(BaseCommand):
    @property
    def name(self) -> str:
        return "query_recovery_media"

    @property
    def description(self) -> str:
        return (
            "- Description: Query media needed for disaster recovery.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "**Output Parameters**:\n"
            "- Volume Name: The media volume.\n"
            "- Storage Pool Name: The associated container."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY RECOVERYMEDIA")

class QueryRetentionMedia(BaseCommand):
    @property
    def name(self) -> str:
        return "query_retention_media"

    @property
    def description(self) -> str:
        return (
            "- Description: Query media moving between retention states (e.g., Vault to Onsite).\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- days (Optional): Number of days matching criteria.\n"
            "**Output Parameters**:\n"
            "- Volume Name: The media volume.\n"
            "- State: Current retention state.\n"
            "- Location: Where the volume is."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "days": {"type": "integer", "description": "Number of days matching criteria."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY RETMEDIA"
        if arguments.get("days"):
            cmd += f" {arguments['days']}"
        return self._execute_simple_query(cmd)

class QueryBackupTOC(BaseCommand):
    @property
    def name(self) -> str:
        return "query_backup_toc"

    @property
    def description(self) -> str:
        return (
            "- Description: Display the Table of Contents (TOC) for a backup image, listing files within it.\n"
            "**Input Parameters**:\n"
            "- client_name (Required): NAS node name. No wildcards.\n"
            "- backup_set_name (Required): File space name. No wildcards.\n"
            "- creation_date (Optional): Creation date of backup image (MM/DD/YYYY). Must be paired with creation_time.\n"
            "- creation_time (Optional): Creation time of backup image (HH:MM:SS). Must be paired with creation_date.\n"
            "- format (Optional): Output format: Standard, Detailed.\n"
            "**Output Parameters**:\n"
            "- File Name: Name of the file in the backup.\n"
            "- Size: Size of the file.\n"
            "- Creation Date: File creation time."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "NAS node name (required). No wildcards."},
                "backup_set_name": {"type": "string", "description": "File space name (required). No wildcards."},
                "creation_date": {"type": "string", "description": "Creation date of backup image (MM/DD/YYYY). Must be paired with creation_time."},
                "creation_time": {"type": "string", "description": "Creation time of backup image (HH:MM:SS). Must be paired with creation_date."},
                "format": {"type": "string", "description": "Output format.", "enum": ["Standard", "Detailed"]}
            },
            "required": ["client_name", "backup_set_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"QUERY TOC {arguments['client_name']} {arguments['backup_set_name']}"
        if arguments.get("creation_date"):
            cmd += f" CREATIONDate={arguments['creation_date']}"
        if arguments.get("creation_time"):
            cmd += f" CREATIONTime={arguments['creation_time']}"
        if arguments.get("format"):
            cmd += f" Format={arguments['format']}"
        return self._execute_simple_query(cmd)
