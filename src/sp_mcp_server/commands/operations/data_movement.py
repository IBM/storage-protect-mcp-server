from typing import Any, Dict
from ..base import BaseCommand

class MoveDataContainer(BaseCommand):
    @property
    def name(self) -> str:
        return "move_data_container"
    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "Moves data from one volume to another within the same or different storage pool. Useful for emptying volumes.\n"
            "**Input Parameters**:\n"
            "- volume_name (Required): The name of the source volume to move data from.\n"
            "- target_pool (Optional): The destination storage pool. If omitted, uses the same pool.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the data movement has started."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "volume_name": {"type": "string", "description": "Source volume."},
                "target_pool": {"type": "string", "description": "Target storage pool."}
            },
            "required": ["volume_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"MOVE DATA {arguments['volume_name']}"
        if arguments.get("target_pool"): cmd += f" STGPOOL={arguments['target_pool']}"
        return self._execute_simple_query(cmd)

class MoveClientData(BaseCommand):
    @property
    def name(self) -> str:
        return "move_client_data"
    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "Moves data belonging to a specific client node to a different storage pool.\n"
            "**Input Parameters**:\n"
            "- client_name (Required): The name of the client node.\n"
            "- source_pool (Required): The source storage pool where data currently resides.\n"
            "- target_pool (Required): The destination storage pool.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the data movement has started."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name."},
                "source_pool": {"type": "string", "description": "Source storage pool."},
                "target_pool": {"type": "string", "description": "Target storage pool."}
            },
            "required": ["client_name", "source_pool", "target_pool"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"MOVE NODEDATA {arguments['client_name']} FROMSTGPOOL={arguments['source_pool']} TOSTGPOOL={arguments['target_pool']}")

class MigrateStorageTarget(BaseCommand):
    @property
    def name(self) -> str:
        return "migrate_storage_target"
    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "Manually triggers data migration for a storage pool. Moves data from higher-level pool (disk) to lower-level pool (tape/cloud).\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): The name of the storage pool to migrate.\n"
            "- low_mig (Optional): The low migration threshold percentage. Migration stops when utilization reaches this.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the migration process has started."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name."},
                "low_mig": {"type": "integer", "description": "Low migration threshold."}
            },
            "required": ["pool_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"MIGRATE STGPOOL {arguments['pool_name']}"
        if arguments.get("low_mig"): cmd += f" LOWMIG={arguments['low_mig']}"
        return self._execute_simple_query(cmd)

class ReclaimStorageSpace(BaseCommand):
    @property
    def name(self) -> str:
        return "reclaim_storage_space"
    @property
    def required_privilege(self) -> str:
        return "storage"
    @property
    def description(self) -> str:
        return (
            "Manually triggers space reclamation for a storage pool. Reclaims fragmented space on sequential access volumes.\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): The name of the storage pool to reclaim.\n"
            "- threshold (Optional): The percentage of reclaimable space required to trigger reclamation for a volume.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the reclamation process has started."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name."},
                "threshold": {"type": "integer", "description": "Reclamation threshold."}
            },
            "required": ["pool_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"RECLAIM STGPOOL {arguments['pool_name']}"
        if arguments.get("threshold"): cmd += f" THRESHOLD={arguments['threshold']}"
        return self._execute_simple_query(cmd)

class QueryBackgroundJob(BaseCommand):
    @property
    def name(self) -> str:
        return "query_background_job"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Display information about currently active background processes/jobs.\n\n"
            "**Input Parameters**:\n"
            "- job_id (Optional): Specific job/process number.\n\n"
            "**Output Parameters**:\n"
            "- Process ID: Unique job identifier.\n"
            "- Description: Type of job (e.g., Migration, Backup).\n"
            "- Status: Current state.\n"
            "- Files/Bytes Processed: Progress metrics."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Specific job/process number. (maps to process_id)"}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY PROCESS"
        if arguments.get("job_id"):
            cmd += f" {arguments['job_id']}"
        return self._execute_simple_query(cmd)

class QueryExportJob(BaseCommand):
    @property
    def name(self) -> str:
        return "query_export_job"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query for active or suspended export operations (data movement out of system).\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- client_name (Optional): node_name to filter export jobs.\n\n"
            "**Output Parameters**:\n"
            "- Process ID: The background job ID.\n"
            "- State: Active or Suspended.\n"
            "- Phase: Export phase."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "client_name": {"type": "string", "description": "Client name to filter export jobs. (maps to node_name)"}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY EXPORT"
        if arguments.get("client_name"):
            cmd += f" NODE={arguments['client_name']}"
        return self._execute_simple_query(cmd)

class QueryMaintenanceJob(BaseCommand):
    @property
    def name(self) -> str:
        return "query_maintenance_job"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query a specific maintenance job.\n\n"
            "**Input Parameters**:\n"
            "- job_id (Optional): Job ID.\n\n"
            "**Output Parameters**:\n"
            "- Job ID: The job identifier.\n"
            "- Type: Type of maintenance.\n"
            "- Status: Current status."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "job_id": {"type": "string", "description": "Job ID."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY JOB"
        if arguments.get("job_id"):
            cmd += f" {arguments['job_id']}"
        return self._execute_simple_query(cmd)

class QueryRestoreJob(BaseCommand):
    @property
    def name(self) -> str:
        return "query_restore_job"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query restartable restore sessions.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Session ID: The restore session.\n"
            "- Node Name: The node restoring.\n"
            "- State: Restartable state."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY RESTORE")
