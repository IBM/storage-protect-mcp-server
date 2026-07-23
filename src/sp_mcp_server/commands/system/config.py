from typing import Any, Dict
from ..base import BaseCommand

class QueryCatalog(BaseCommand):
    @property
    def name(self) -> str:
        return "query_catalog"

    @property
    def description(self) -> str:
        return (
            "- Description: Display information about the server's metadata catalog (database).\n\n"
            "**Note**: This is a read-only tool. There is currently **no tool** to extend or increase the database size.\n\n"
            "**Input Parameters**:\n"
            "- format (Optional): Level of detail (standard, detailed).\n\n"
            "**Output Parameters**:\n"
            "- Available Space: Total space assigned to the catalog.\n"
            "- Assigned Capacity: Space actually allocated.\n"
            "- Maximum Extension: How much the catalog can grow.\n"
            "- Pages/Usable Pages: Internal database page metrics.\n"
            "- Used Space: Percentage of catalog space currently used."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["standard", "detailed"],
                    "description": "Level of detail for the output (standard or detailed).",
                    "default": "standard"
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        base_cmd = "QUERY DB"
        if arguments.get("format") == "detailed":
            base_cmd += " FORMAT=DETAILED"
        return self._execute_simple_query(base_cmd)

class QueryCatalogSpace(BaseCommand):
    @property
    def name(self) -> str:
        return "query_catalog_space"

    @property
    def description(self) -> str:
        return (
            "- Description: Display storage space utilization for the metadata catalog (database).\n\n"
            "**Note**: This is a read-only tool. There is currently **no tool** to extend or increase the database size.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Location: Directory or path of the catalog storage.\n"
            "- Total Space: Total capacity of the directory.\n"
            "- Used Space: Space currently used by the catalog.\n"
            "- Free Space: Available space for growth."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY DBSPACE")

class QuerySystemInfo(BaseCommand):
    @property
    def name(self) -> str:
        return "query_system_info"

    @property
    def description(self) -> str:
        return (
            "- Description: Query hardware and system information from a client or the server.\n\n"
            "**Input Parameters**:\n"
            "- client_name (Optional): Name of the client/workload to query.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: Name of the client/system.\n"
            "- Platform: Operating system platform.\n"
            "- Processor Info: Details about the CPU architecture.\n"
            "- RAM: Total memory available."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                 "client_name": {"type": "string", "description": "Name of the client/workload to query (maps to node_name)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY MACHINE"
        if arguments.get("client_name"):
            cmd += f" {arguments['client_name']}"
        return self._execute_simple_query(cmd)

class QueryMonitoringConfig(BaseCommand):
    @property
    def name(self) -> str:
        return "query_monitoring_config"

    @property
    def description(self) -> str:
        return (
            "- Description: Display configuration settings for system monitoring.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Setting Name: The monitoring option.\n"
            "- Value: Current configuration value."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY MONITORSETTINGS")

class QueryMonitoringStatus(BaseCommand):
    @property
    def name(self) -> str:
        return "query_monitoring_status"

    @property
    def description(self) -> str:
        return (
            "- Description: Display current status of system monitors.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Monitor Name: Name of the monitor.\n"
            "- Status: Active/Inactive status."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY STATUS")
