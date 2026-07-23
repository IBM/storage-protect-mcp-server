from typing import Any, Dict
from ..base import BaseCommand

class DefineClientOptSet(BaseCommand):
    @property
    def name(self) -> str:
        return "define_client_opt_set"
    
    @property
    def description(self) -> str:
        return (
            "Defines a **Client Option Set** in SP. This profile contains a set of rules (like include/exclude filters) that can be applied to Nodes.\n"
            "**Input Parameters**:\n"
            "- option_set_name (Required): Unique name for the configuration profile.\n"
            "- description (Optional): Description of the profile's purpose.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the profile was created."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "option_set_name": {"type": "string", "description": "Option set name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["option_set_name"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE CLOPTSET {arguments['option_set_name']}"
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class DefineClientOpt(BaseCommand):
    @property
    def name(self) -> str:
        return "define_client_opt"
    
    @property
    def description(self) -> str:
        return (
            "Adds a specific configuration rule (Option) to a **Client Option Set**. For example, adding an 'INCLUDE' or 'EXCLUDE' rule.\n"
            "**Input Parameters**:\n"
            "- option_set_name (Required): Name of the profile to modify.\n"
            "- option_name (Required): The setting name (e.g., 'DIRMC', 'INCLUDE', 'EXCLUDE').\n"
            "- option_value (Required): The value for the setting (e.g., file pattern).\n"
            "- seq_number (Optional): Sequence number to order the rule.\n"
            "- force (Optional): 'YES' or 'NO' to force the option on the client.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the rule was added."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "option_set_name": {"type": "string", "description": "Option set name."},
                "option_name": {"type": "string", "description": "Option name."},
                "option_value": {"type": "string", "description": "Option value."},
                "seq_number": {"type": "integer", "description": "Sequence number."},
                "force": {"type": "string", "enum": ["YES", "NO"], "description": "Force option."}
            },
            "required": ["option_set_name", "option_name", "option_value"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE CLIENTOPT {arguments['option_set_name']} {arguments['option_name']} \"{arguments['option_value']}\""
        if arguments.get("seq_number"):
            cmd += f" SEQNUMBER={arguments['seq_number']}"
        if arguments.get("force"):
            cmd += f" FORCE={arguments['force']}"
        return self._execute_simple_query(cmd)

class UpdateClientOptSet(BaseCommand):
    @property
    def name(self) -> str:
        return "update_client_opt_set"
    @property
    def description(self) -> str:
        return (
            "Updates the description of a **Client Option Set**.\n"
            "**Input Parameters**:\n"
            "- option_set_name (Required): The name of the option set.\n"
            "- description (Optional): The new description.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the option set was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "option_set_name": {"type": "string", "description": "Option set name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["option_set_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE CLOPTSET {arguments['option_set_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class UpdateClientOpt(BaseCommand):
    @property
    def name(self) -> str:
        return "update_client_opt"
    @property
    def description(self) -> str:
        return (
            "Updates a specific **Client Option** within a set. Can change the sequence number or force flag.\n"
            "**Input Parameters**:\n"
            "- option_set_name (Required): The name of the option set.\n"
            "- option_name (Required): The option name.\n"
            "- seq_number (Required): The existing sequence number to identify the option.\n"
            "- new_seq_number (Required): The new sequence number to assign.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the option was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "option_set_name": {"type": "string", "description": "Option set name."},
                "option_name": {"type": "string", "description": "Option name."},
                "seq_number": {"type": "integer", "description": "Old sequence number to identify."},
                "new_seq_number": {"type": "integer", "description": "New sequence number."}
            },
            "required": ["option_set_name", "option_name", "seq_number", "new_seq_number"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        # Syntax: UPDATE CLIENTOPT setname optname seqnumber newseqnumber
        cmd = f"UPDATE CLIENTOPT {arguments['option_set_name']} {arguments['option_name']} {arguments['seq_number']} {arguments['new_seq_number']}"
        return self._execute_simple_query(cmd)

class UpdateProfile(BaseCommand):
    @property
    def name(self) -> str:
        return "update_profile"
    @property
    def description(self) -> str:
        return (
            "Updates a **Profile** description. Profiles are used to subscribing to configuration info.\n"
            "**Input Parameters**:\n"
            "- profile_name (Required): The name of the profile.\n"
            "- description (Optional): The new description.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the profile was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "profile_name": {"type": "string", "description": "Profile name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["profile_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE PROFILE {arguments['profile_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class DeleteClientOptSet(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_client_opt_set"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Client Option Set**.\n"
            "**Input Parameters**:\n"
            "- option_set_name (Required): The name of the option set to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the option set was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "option_set_name": {"type": "string", "description": "Option set name."}
            },
            "required": ["option_set_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE CLOPTSET {arguments['option_set_name']}")

class DeleteClientOpt(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_client_opt"
    @property
    def description(self) -> str:
        return (
            "Deletes a specific **Client Option** from a set.\n"
            "**Input Parameters**:\n"
            "- option_set_name (Required): The name of the option set.\n"
            "- option_name (Required): The option name to remove.\n"
            "- seq_number (Optional): Specific sequence number.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the option was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "option_set_name": {"type": "string", "description": "Option set name."},
                "option_name": {"type": "string", "description": "Option name."},
                "seq_number": {"type": "integer", "description": "Sequence number (optional if unique)."}
            },
            "required": ["option_set_name", "option_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DELETE CLIENTOPT {arguments['option_set_name']} {arguments['option_name']}"
        if arguments.get("seq_number"): cmd += f" SEQNUMBER={arguments['seq_number']}"
        return self._execute_simple_query(cmd)

class QueryClientOptionSet(BaseCommand):
    @property
    def name(self) -> str:
        return "query_client_option_set"

    @property
    def description(self) -> str:
        return (
            "Query node option sets, which centralize node configuration.\n\n"
            "**Input Parameters**:\n"
            "- option_set (Optional): Name of the option set.\n\n"
            "**Output Parameters**:\n"
            "- Option Set Name: Name of the set.\n"
            "- Option: The configuration option (e.g., INCLUDE/EXCLUDE).\n"
            "- Value: The value of the option."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "option_set": {"type": "string", "description": "Name of the option set."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY CLOPTSET"
        if arguments.get("option_set"):
            cmd += f" {arguments['option_set']}"
        return self._execute_simple_query(cmd)
