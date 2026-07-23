from typing import Any, Dict
from ..base import BaseCommand

class QueryDRStatus(BaseCommand):
    @property
    def name(self) -> str:
        return "query_dr_status"

    @property
    def description(self) -> str:
        return (
            "Display the current settings and status for the Disaster Recovery Manager (DRM).\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Parameter: The DRM setting.\n"
            "- Value: Current value."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY DRMSTATUS")

class QueryDRMedia(BaseCommand):
    @property
    def name(self) -> str:
        return "query_dr_media"

    @property
    def description(self) -> str:
        return (
            "Display information about disaster recovery media (tapes/volumes) tracked by DRM.\n\n"
            "**Input Parameters**:\n"
            "- source_db (Optional): Filter by source database type.\n\n"
            "**Output Parameters**:\n"
            "- Volume Name: The media volume.\n"
            "- State: Current state (e.g., MOUNTABLE, VAULT).\n"
            "- Location: Physical location."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "source_db": {"type": "string", "enum": ["dbbackup", "dbsnapshot", "dbvol"], "description": "Filter by source database type."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY DRMEDIA"
        if arguments.get("source_db"):
            cmd += f" {arguments['source_db']}"
        return self._execute_simple_query(cmd)

class QueryRecoveryPlanFile(BaseCommand):
    @property
    def name(self) -> str:
        return "query_recovery_plan_file"

    @property
    def description(self) -> str:
        return (
            "Query recovery plan file information stored on a target server.\n\n"
            "**Input Parameters**:\n"
            "- devclass (Optional): Device class used to create the plan files. Use when logged onto the server that created the plan.\n"
            "- nodename (Optional): Node name of the source server. Use when logged onto the target server.\n"
            "- source (Optional): DB backup type used when plan was prepared. Values: DBBackup, DBSnapshot. Default: DBBackup.\n"
            "- format (Optional): Display format. Values: Standard, Detailed. Default: Standard.\n\n"
            "**Output Parameters**:\n"
            "- Date/Time: When the plan was saved.\n"
            "- Machine: Source machine."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "devclass": {
                    "type": "string",
                    "description": "Device class used to create the recovery plan files. Wildcards supported. Use when logged onto the server that created the plan."
                },
                "nodename": {
                    "type": "string",
                    "description": "Node name on the target server of the source server that created the plan files. Wildcards supported."
                },
                "source": {
                    "type": "string",
                    "description": "Type of DB backup used when plan was prepared. Default: DBBACKUP.",
                    "enum": ["DBBackup", "DBSnapshot"]
                },
                "format": {
                    "type": "string",
                    "description": "Display format. Default: STANDARD.",
                    "enum": ["Standard", "Detailed"]
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY RPFILE"
        if arguments.get("devclass"):
            cmd += f" DEVclass={arguments['devclass']}"
        if arguments.get("nodename"):
            cmd += f" NODEName={arguments['nodename']}"
        if arguments.get("source"):
            cmd += f" Source={arguments['source']}"
        if arguments.get("format"):
            cmd += f" Format={arguments['format']}"
        return self._execute_simple_query(cmd)

class QueryRecoveryPlanFileContent(BaseCommand):
    @property
    def name(self) -> str:
        return "query_recovery_plan_file_content"

    @property
    def description(self) -> str:
        return (
            "Display the contents of a recovery plan file stored on a target server.\n\n"
            "**Input Parameters**:\n"
            "- plan_file_name (Required): Name of the recovery plan file. Format: servername.yyyymmdd.hhmmss. Use query_recovery_plan_file to list existing files.\n"
            "- devclass (Optional): Device class used to create the file. Use when issuing from the source server.\n"
            "- nodename (Optional): Node name of the source server registered on the target server. Use when issuing from the target server.\n\n"
            "**Output Parameters**:\n"
            "- Line Number: Line index.\n"
            "- Content: Plan instructions."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "plan_file_name": {
                    "type": "string",
                    "description": "Name of the recovery plan file to query. Format: servername.yyyymmdd.hhmmss. Use query_recovery_plan_file to get existing file names."
                },
                "devclass": {
                    "type": "string",
                    "description": "Device class used to create the recovery plan file. No wildcards. Use when issuing from the source server."
                },
                "nodename": {
                    "type": "string",
                    "description": "Node name of the source server registered on the target server. No wildcards. Use when issuing from the target server."
                }
            },
            "required": ["plan_file_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"QUERY RPFCONTENT {arguments['plan_file_name']}"
        if arguments.get("devclass"):
            cmd += f" DEVclass={arguments['devclass']}"
        if arguments.get("nodename"):
            cmd += f" NODEName={arguments['nodename']}"
        return self._execute_simple_query(cmd)

class BackupDB(BaseCommand):
    @property
    def name(self) -> str:
        return "backup_db"

    @property
    def description(self) -> str:
        return (
            "Backs up the **Server Database** (DB). This is a critical operation for disaster recovery.\n"
            "**Input Parameters**:\n"
            "- type (Required): 'FULL' or 'INCREMENTAL'.\n"
            "- devclass (Optional): Device class to use for the backup.\n"
            "- scratch (Optional): 'YES' or 'NO' to use scratch volumes.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the backup started."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["FULL", "INCREMENTAL"], "description": "Type of backup."},
                "devclass": {"type": "string", "description": "Device class to use."},
                "scratch": {"type": "string", "enum": ["YES", "NO"], "description": "Use scratch volumes."}
            },
            "required": ["type"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"BACKUP DB TYPE={arguments['type']}"
        if arguments.get("devclass"):
            cmd += f" DEVCLASS={arguments['devclass']}"
        if arguments.get("scratch"):
            cmd += f" SCRATCH={arguments['scratch']}"
        return self._execute_simple_query(cmd)

class RestoreDB(BaseCommand):
    @property
    def name(self) -> str:
        return "restore_db"

    @property
    def description(self) -> str:
        return (
            "Restores the **Server Database** (DB) from a backup. **WARNING**: This stops the server and overwrites the existing DB.\n"
            "**Input Parameters**:\n"
            "- to_date (Optional): Restore to specific date.\n"
            "- to_time (Optional): Restore to specific time.\n"
            "- source (Optional): 'DBBACKUP' or 'DBSNAPSHOT'.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the restore process started."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "to_date": {"type": "string", "description": "Restore to date."},
                "to_time": {"type": "string", "description": "Restore to time."},
                "source": {"type": "string", "enum": ["DBBACKUP", "DBSNAPSHOT"], "description": "Source of restore."}
            },
            "required": []
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "RESTORE DB"
        if arguments.get("to_date"):
            cmd += f" TODATE={arguments['to_date']}"
        if arguments.get("to_time"):
            cmd += f" TOTIME={arguments['to_time']}"
        if arguments.get("source"):
            cmd += f" SOURCE={arguments['source']}"
        return self._execute_simple_query(cmd)
