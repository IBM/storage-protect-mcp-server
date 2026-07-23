from typing import Any, Dict
from ..base import BaseCommand

class DefinePolicySet(BaseCommand):
    @property
    def name(self) -> str:
        return "define_policy_set"
    
    @property
    def description(self) -> str:
        return (
            "Defines a **Policy Set** within a domain. Contains a collection of management classes that can be activated together.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The parent Policy Domain.\n"
            "- policy_set_name (Required): Name for the new Policy Set.\n"
            "- description (Optional): Description.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the profile was defined."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["domain_name", "policy_set_name"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE POLICYSET {arguments['domain_name']} {arguments['policy_set_name']}"
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class UpdatePolicySet(BaseCommand):
    @property
    def name(self) -> str:
        return "update_policy_set"
    @property
    def description(self) -> str:
        return (
            "Updates an existing **Policy Set** description or default management class.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The parent Policy Domain.\n"
            "- policy_set_name (Required): The name of the Policy Set to update.\n"
            "- description (Optional): The new description.\n"
            "- defmgmtclass (Optional): Name of the default management class for this policy set.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the policy set was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."},
                "description": {"type": "string", "description": "New description."},
                "defmgmtclass": {"type": "string", "description": "Name of the default management class for this policy set."}
            },
            "required": ["domain_name", "policy_set_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE POLICYSET {arguments['domain_name']} {arguments['policy_set_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        if arguments.get("defmgmtclass"): cmd += f" DEFMGMTCLASS={arguments['defmgmtclass']}"
        return self._execute_simple_query(cmd)

class ActivatePolicySet(BaseCommand):
    @property
    def name(self) -> str:
        return "activate_policy_set"
    @property
    def description(self) -> str:
        return (
            "Activates a **Policy Set**. This makes the policy set the effective policy for the domain, applying retention and management rules.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The name of the policy domain.\n"
            "- profile_name (Required): The name of the Policy Set to activate.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the policy set was activated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "profile_name": {"type": "string", "description": "Profile (Policy Set) name."}
            },
            "required": ["domain_name", "profile_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"ACTIVATE POLICYSET {arguments['domain_name']} {arguments['profile_name']}")

class ValidatePolicySet(BaseCommand):
    @property
    def name(self) -> str:
        return "validate_policy_set"
    @property
    def description(self) -> str:
        return (
            "Validates the consistency and completeness of a **Policy Set** before deployment.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The name of the policy domain.\n"
            "- profile_name (Required): The name of the Policy Set to validate.\n"
            "**Output Parameters**:\n"
            "- Result: Success message or list of validation errors."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "profile_name": {"type": "string", "description": "Profile (Policy Set) name."}
            },
            "required": ["domain_name", "profile_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"VALIDATE POLICYSET {arguments['domain_name']} {arguments['profile_name']}")

class DeletePolicySet(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_policy_set"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Policy Set**.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Parent Policy Domain.\n"
            "- policy_set_name (Required): Name of the Policy Set to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the policy set was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."}
            },
            "required": ["domain_name", "policy_set_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE POLICYSET {arguments['domain_name']} {arguments['policy_set_name']}")

class QueryPolicySet(BaseCommand):
    @property
    def name(self) -> str:
        return "query_policy_set"

    @property
    def description(self) -> str:
        return (
            "Queries **Policy Sets**. A collection of policy sets that can be validated and activated.\n"
            "**Input Parameters**:\n"
            "- policy_group (Optional): Parent Policy Domain.\n"
            "- policy_set (Optional): Specific profile name.\n"
            "**Output Parameters**:\n"
            "- Policy Domain Name: Parent domain.\n"
            "- Policy Set Name: Profile name.\n"
            "- Description: Profile description."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "policy_group": {"type": "string", "description": "Policy group name."},
                "policy_set": {"type": "string", "description": "Policy set name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY POLICYSET"
        if arguments.get("policy_group"):
            cmd += f" {arguments['policy_group']}"
        if arguments.get("policy_set"):
            cmd += f" {arguments['policy_set']}"
        return self._execute_simple_query(cmd)
