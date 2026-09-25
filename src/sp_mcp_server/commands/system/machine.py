from typing import Any, Dict
from ..base import BaseCommand

class DefineMachine(BaseCommand):
    @property
    def name(self) -> str:
        return "define_machine"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Define a **Machine** (Client) manually, declaring its existence to the server.\n\n"
            "**Input Parameters**:\n"
            "- machine_name (Required): The name of the machine to define.\n"
            "- description (Optional): Description of the machine.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the machine was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "machine_name": {"type": "string"},
                "description": {"type": "string"}
            },
            "required": ["machine_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        # Note: DEFINE MACHINE isn't a standard command in some versions (usually REGISTER NODE),
        # but matching the structure from previous files.
        cmd = f"DEFINE MACHINE {arguments['machine_name']}"
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class UpdateMachine(BaseCommand):
    @property
    def name(self) -> str:
        return "update_machine"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Updates properties of a registered **Machine** (Client).\n\n"
            "**Input Parameters**:\n"
            "- machine_name (Required): The name of the machine.\n"
            "- description (Optional): New description for the machine.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the machine was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "machine_name": {"type": "string", "description": "Machine name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["machine_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE MACHINE {arguments['machine_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class DeleteMachine(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_machine"
    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Machine** (Client) definition.\n\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- machine_name (Required): The name of the machine to delete.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the machine was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "machine_name": {"type": "string", "description": "Machine name."}
            },
            "required": ["machine_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE MACHINE {arguments['machine_name']}")
