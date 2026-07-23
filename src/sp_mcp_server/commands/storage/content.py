from typing import Any, Dict
from ..base import BaseCommand

class QueryDamagedData(BaseCommand):
    @property
    def name(self) -> str:
        return "query_damaged_data"

    @property
    def description(self) -> str:
        return (
            "- Description: Query data marked as damaged within storage containers.\n\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): Directory-container or cloud storage pool name.\n"
            "- type (Optional): Type of information to display. Values: Status, Node, INVentory, CONTAiner.\n"
            "- node_name (Optional): Filter results to a single node.\n\n"
            "**Output Parameters**:\n"
            "- Storage Pool Name: The container.\n"
            "- Object ID: ID of the damaged object.\n"
            "- Type: Type of damage."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Directory-container or cloud storage pool name (required)."},
                "type": {
                    "type": "string",
                    "description": "Type of information to display.",
                    "enum": ["Status", "Node", "INVentory", "CONTAiner"]
                },
                "node_name": {"type": "string", "description": "Filter results to a single node (NODENAME=)."}
            },
            "required": ["pool_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"QUERY DAMAGED {arguments['pool_name']}"
        if arguments.get("type"):
            cmd += f" TYPE={arguments['type']}"
        if arguments.get("node_name"):
            cmd += f" NODENAME={arguments['node_name']}"
        return self._execute_simple_query(cmd)

class QueryContainerCleanup(BaseCommand):
    @property
    def name(self) -> str:
        return "query_container_cleanup"

    @property
    def description(self) -> str:
        return (
            "- Description: Query the cleanup process status for source storage containers.\n\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): Storage pool name to query.\n\n"
            "**Output Parameters**:\n"
            "- Storage Pool Name: The container.\n"
            "- Phase: Cleanup phase.\n"
            "- Status: Current status."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name to query (required)."}
            },
            "required": ["pool_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"QUERY CLEANUP {arguments['pool_name']}")

class QueryContainerConversion(BaseCommand):
    @property
    def name(self) -> str:
        return "query_container_conversion"

    @property
    def description(self) -> str:
        return (
            "- Description: Query the status of storage container conversion (e.g., changing format).\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Process: The conversion process info.\n"
            "- Status: Status of conversion."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY CONVERSION")

class QueryDeduplicationStats(BaseCommand):
    @property
    def name(self) -> str:
        return "query_deduplication_stats"

    @property
    def description(self) -> str:
        return (
            "- Description: Query statistics related to data deduplication savings in storage containers.\n\n"
            "**Input Parameters**:\n"
            "- container_name (Optional): Storage container name.\n\n"
            "**Output Parameters**:\n"
            "- Storage Pool Name: The container.\n"
            "- Total Data Protected: Logical amount of data.\n"
            "- Total Space Used: Physical space used.\n"
            "- Deduplication Ratio: Efficiency ratio."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "container_name": {"type": "string", "description": "Storage container name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY DEDUPSTATS"
        if arguments.get("container_name"):
            cmd += f" STGPOOL={arguments['container_name']}"
        return self._execute_simple_query(cmd)

class QueryExtentUpdates(BaseCommand):
    @property
    def name(self) -> str:
        return "query_extent_updates"

    @property
    def description(self) -> str:
        return (
            "- Description: Query information about updated data extents in the system.\n\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): Storage pool name to query.\n\n"
            "**Output Parameters**:\n"
            "- Extent ID: Identifier for the data chunk.\n"
            "- Status: Status of the update."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name to query (required)."}
            },
            "required": ["pool_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"QUERY EXTENTUPDATES {arguments['pool_name']}")

class QueryShreddingStatus(BaseCommand):
    @property
    def name(self) -> str:
        return "query_shredding_status"

    @property
    def description(self) -> str:
        return (
            "- Description: Query the status of secure data shredding operations.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Shredding Active: Yes/No.\n"
            "- Passes: Number of overwrite passes."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY SHREDSTATUS")
