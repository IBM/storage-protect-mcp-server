from typing import Any, Dict
from ..base import BaseCommand

class DefinePolicyDomain(BaseCommand):
    @property
    def name(self) -> str:
        return "define_policy_domain"
    
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Defines a new **Policy Domain** (SLA). a logical grouping of clients with similar backup requirements.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Unique name for the Policy Domain.\n"
            "- description (Optional): Description of the domain's purpose.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the domain was defined."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["domain_name"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE DOMAIN {arguments['domain_name']}"
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class UpdatePolicyDomain(BaseCommand):
    @property
    def name(self) -> str:
        return "update_policy_domain"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Updates the description of an existing **Policy Domain** (SLA).\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The name of the policy domain to update.\n"
            "- description (Optional): The new description for the domain.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the domain was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "description": {"type": "string", "description": "New description."}
            },
            "required": ["domain_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE DOMAIN {arguments['domain_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class UpdateObjectDomain(BaseCommand):
    @property
    def name(self) -> str:
        return "update_object_domain"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Updates an existing **Object Policy Domain**.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Domain name.\n"
            "- description (Optional): New description.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the domain was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["domain_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE OBJECTDOMAIN {arguments['domain_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class DeletePolicyDomain(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_policy_domain"
    @property
    def required_privilege(self) -> str:
        return "policy"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Policy Domain** (SLA). Use carefully as it can impact all assigned clients.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Name of the domain to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the domain was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."}
            },
            "required": ["domain_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE DOMAIN {arguments['domain_name']}")

class QueryPolicyGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "query_policy_group"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Queries **Policy Domains**. Defines distinct SLAs or business groups for nodes.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- domain_name (Optional): Specific Policy Domain name to query. (historically `policy_group` in code)\n"
            "**Output Parameters**:\n"
            "- Policy Domain Name: The domain identifier.\n"
            "- Activated Policy Set: The currently active Policy Set enforcing rules.\n"
            "- Description: Domain description."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "isp_server_name": {"type": "string", "description": "Target ISP Server name from registry (optional)."},

                "domain_name": {"type": "string", "description": "Specific Policy Domain name to query."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY DOMAIN"
        if arguments.get("domain_name"):
            cmd += f" {arguments['domain_name']}"
        return self._execute_simple_query(cmd)

class QueryLegalHold(BaseCommand):
    @property
    def name(self) -> str:
        return "query_legal_hold"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query active legal holds prevents deletion of data regardless of retention rules.\n\n"
            "**Input Parameters**:\n"
            "- hold_name (Optional): Name of the hold.\n\n"
            "**Output Parameters**:\n"
            "- Hold Name: Name of the hold.\n"
            "- Description: Reason for the hold."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "hold_name": {"type": "string"}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY HOLD"
        if arguments.get("hold_name"):
             cmd += f" {arguments['hold_name']}"
        return self._execute_simple_query(cmd)

class QueryLegalHoldLog(BaseCommand):
    @property
    def name(self) -> str:
        return "query_legal_hold_log"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "Query the audit log of legal hold operations (creation, release).\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Date/Time: When the action occurred.\n"
            "- Admin: Who performed the action.\n"
            "- Message: Details of the operation."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY HOLDLOG")
