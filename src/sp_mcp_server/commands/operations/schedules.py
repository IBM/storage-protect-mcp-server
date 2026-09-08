from typing import Any, Dict
from ..base import BaseCommand

class DefineClientAction(BaseCommand):
    @property
    def name(self) -> str:
        return "define_client_action"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Define a **Node Action** (one-time schedule). Forces a node operation (e.g., backup) immediately or shortly.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- node_name (Required): The node name (or * for all).\n"
            "- action (Required): The action to perform (e.g., INCREMENTAL).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the action was scheduled."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {"type": "string", "description": "Node name (or *)."},
                "action": {"type": "string", "description": "Action (e.g. INCREMENTAL)."}
            },
            "required": ["node_name", "action"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DEFINE CLIENTACTION {arguments['node_name']} ACTION={arguments['action']}")
