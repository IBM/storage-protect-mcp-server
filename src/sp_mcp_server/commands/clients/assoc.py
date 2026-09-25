from typing import Any, Dict
from ..base import BaseCommand

class DefineAssociation(BaseCommand):
    @property
    def name(self) -> str:
        return "define_association"
    
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Associates **Nodes** with a **Schedule** to automate backup operations.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The Policy Domain where the schedule exists.\n"
            "- schedule_name (Required): The name of the Schedule.\n"
            "- node_names (Required): Space-separated list of node names to associate.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the association was created."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "schedule_name": {"type": "string", "description": "Schedule name."},
                "node_names": {"type": "string", "description": "Node names (space separated)."}
            },
            "required": ["domain_name", "schedule_name", "node_names"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE ASSOCIATION {arguments['domain_name']} {arguments['schedule_name']} {arguments['node_names']}"
        return self._execute_simple_query(cmd)

class DeleteAssociation(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_association"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Node Association** with a schedule.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Policy domain.\n"
            "- schedule_name (Required): Schedule name.\n"
            "- node_names (Required): Node name(s) to disassociate.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the association was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "schedule_name": {"type": "string", "description": "Schedule name."},
                "node_names": {"type": "string", "description": "Node names (or specific node)."}
            },
            "required": ["domain_name", "schedule_name", "node_names"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE ASSOCIATION {arguments['domain_name']} {arguments['schedule_name']} {arguments['node_names']}")
