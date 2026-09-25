from typing import Any, Dict
from ..base import BaseCommand

class DefineHold(BaseCommand):
    @property
    def name(self) -> str:
        return "define_hold"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Define a **Hold** on retention set data. Prevents deletion of retention sets until the hold is released.\n"
            "**Input Parameters**:\n"
            "- hold_name (Required): The name of the hold to define.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the hold was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hold_name": {"type": "string", "description": "Hold name."}
            },
            "required": ["hold_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DEFINE HOLD {arguments['hold_name']}")

class DeleteHold(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_hold"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Hold** on retention set data.\n"
            "**Input Parameters**:\n"
            "- hold_name (Required): The name of the hold to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the hold was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hold_name": {"type": "string", "description": "Hold name."}
            },
            "required": ["hold_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE HOLD {arguments['hold_name']}")

class DefineRetentionRule(BaseCommand):
    @property
    def name(self) -> str:
        return "define_retention_rule"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Define a **Retention Rule** for managing long-term data retention (Retention Sets).\n"
            "**Input Parameters**:\n"
            "- rule_name (Required): The name of the retention rule.\n"
            "- node_name (Required): The node name pattern to apply the rule to.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the rule was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Rule name."},
                "node_name": {"type": "string", "description": "Node name pattern."}
            },
            "required": ["rule_name", "node_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DEFINE RETRULE {arguments['rule_name']} NODE={arguments['node_name']}")
