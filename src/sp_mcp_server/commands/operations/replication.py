from typing import Any, Dict
from ..base import BaseCommand

class QueryProtectionStatus(BaseCommand):
    @property
    def name(self) -> str:
        return "query_protection_status"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query the status of storage pool protection operations (e.g., replication to target).\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Storage Pool: The source pool.\n"
            "- Protection Status: Synced or not."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY PROTECTSTATUS")

class QueryReplicationFailures(BaseCommand):
    @property
    def name(self) -> str:
        return "query_replication_failures"
    
    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query detailed data about replication failures.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: The node that failed.\n"
            "- File Space: The backup volume that failed.\n"
            "- Failure Date: Time of failure."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY REPLFAILURES")

class QueryReplicationStatus(BaseCommand):
    @property
    def name(self) -> str:
        return "query_replication_status"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query active node replication processes.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- node_name (Required): Node name to query replication status for.\n\n"
            "**Output Parameters**:\n"
            "- Node Name: Node being replicated.\n"
            "- Bytes Replicated: Data moved.\n"
            "- Status: Current activity.\n\n"
            "**Note**: IBM Storage Protect requires a node name for QUERY REPLICATION. "
            "If no active replication is found for the specified node, the command returns 'No match found'."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "isp_server_name": {"type": "string", "description": "Target ISP Server name from registry (optional)."},
                "node_name": {"type": "string", "description": "Node name (required)."}
            },
            "required": ["node_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        node_name = arguments.get("node_name")
        if not node_name:
            return "Error: node_name parameter is required for QUERY REPLICATION command."
        cmd = f"QUERY REPLICATION {node_name}"
        return self._execute_simple_query(cmd)

class QueryReplicationRule(BaseCommand):
    @property
    def name(self) -> str:
        return "query_replication_rule"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query rules governing replication behavior.\n\n"
            "**Input Parameters**:\n"
            "- rule_name (Optional): Rule name.\n\n"
            "**Output Parameters**:\n"
            "- Rule Name: Name of the rule.\n"
            "- Priority: Execution priority."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Rule name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY REPLRULE"
        if arguments.get("rule_name"):
            cmd += f" {arguments['rule_name']}"
        return self._execute_simple_query(cmd)

class QueryReplicationServer(BaseCommand):
    @property
    def name(self) -> str:
        return "query_replication_server"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query a defined replication server.\n\n"
            "**Input Parameters**:\n"
            "- server_name (Optional): Server name.\n\n"
            "**Output Parameters**:\n"
            "- Server Name: The partner server.\n"
            "- Server Address: Network location."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "server_name": {"type": "string", "description": "Server name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY REPLSERVER"
        if arguments.get("server_name"):
            cmd += f" {arguments['server_name']}"
        return self._execute_simple_query(cmd)
