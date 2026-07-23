from typing import Any, Dict
from ..base import BaseCommand

class DefineManagementClass(BaseCommand):
    @property
    def name(self) -> str:
        return "define_management_class"
    
    @property
    def description(self) -> str:
        return (
            "Defines a **Management Class** (also known as a Retention Policy in IBM SP terminology). A management class is the binding point users apply to individual files or objects to specify how they are managed; it contains one or more Copy Groups that define versioning and retention behavior.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Parent Policy Domain.\n"
            "- policy_set_name (Required): Parent Policy Set.\n"
            "- class_name (Required): Name for the Management Class (policy object).\n"
            "- description (Optional): Description.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the policy was defined."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."},
                "class_name": {"type": "string", "description": "Management class name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["domain_name", "policy_set_name", "class_name"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE MGMTCLASS {arguments['domain_name']} {arguments['policy_set_name']} {arguments['class_name']}"
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class UpdateManagementClass(BaseCommand):
    @property
    def name(self) -> str:
        return "update_management_class"
    @property
    def description(self) -> str:
        return (
            "Updates a **Management Class** (policy object) description.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The parent Policy Domain.\n"
            "- policy_set_name (Required): The parent Policy Set.\n"
            "- class_name (Required): The name of the Management Class (policy object).\n"
            "- description (Optional): The new description.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the management class was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."},
                "class_name": {"type": "string", "description": "Class name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["domain_name", "policy_set_name", "class_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE MGMTCLASS {arguments['domain_name']} {arguments['policy_set_name']} {arguments['class_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)

class DeleteManagementClass(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_management_class"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Management Class** (policy object).\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Parent Policy Domain.\n"
            "- policy_set_name (Required): Parent Policy Set.\n"
            "- class_name (Required): Name of the Management Class to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the management class was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."},
                "class_name": {"type": "string", "description": "Class name."}
            },
            "required": ["domain_name", "policy_set_name", "class_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE MGMTCLASS {arguments['domain_name']} {arguments['policy_set_name']} {arguments['class_name']}")

class AssignDefMgmtClass(BaseCommand):
    @property
    def name(self) -> str:
        return "assign_defmgmtclass"
    
    @property
    def description(self) -> str:
        return (
            "Assigns a **Default Management Class** to a policy set. This is REQUIRED before a policy set can be validated or activated.\n"
            "This is the PRIMARY command for setting the default management class (preferred over UPDATE POLICYSET with DEFMGMTCLASS parameter).\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): The policy domain containing the policy set.\n"
            "- policy_set_name (Required): The policy set to assign the default management class to. Note: Cannot assign to ACTIVE policy set.\n"
            "- class_name (Required): The management class to set as default. Should contain both archive and backup copy groups.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the default management class was assigned."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Policy domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name (cannot be ACTIVE)."},
                "class_name": {"type": "string", "description": "Management class name to set as default."}
            },
            "required": ["domain_name", "policy_set_name", "class_name"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"ASSIGN DEFMGMTCLASS {arguments['domain_name']} {arguments['policy_set_name']} {arguments['class_name']}"
        return self._execute_simple_query(cmd)

class QueryProtectionPolicy(BaseCommand):
    @property
    def name(self) -> str:
        return "query_protection_policy"

    @property
    def description(self) -> str:
        return (
            "Queries **Management Classes**. Returns management-class objects that are used to bind policies to files and reference Copy Groups.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- domain_name (Optional): Parent Policy Domain. (historically `policy_group`)\n"
            "- policy_set (Optional): Parent profile.\n"
            "- policy_name (Optional): Specific Management Class name.\n"
            "**Output Parameters**:\n"
            "- Policy Domain: Parent domain.\n"
            "- Policy Set: Parent profile.\n"
            "- Mgmt Class Name: Service level identifier.\n"
            "- Default Mgmt Class: Indicates if this is the default policy."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "isp_server_name": {"type": "string", "description": "Target ISP Server name from registry (optional)."},

                "domain_name": {"type": "string", "description": "Parent Policy Domain."},
                "policy_set": {"type": "string", "description": "Policy set name."},
                "policy_name": {"type": "string", "description": "Protection policy/Management class name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY MGMTCLASS"
        if arguments.get("domain_name"):
            cmd += f" {arguments['domain_name']}"
        if arguments.get("policy_set"):
            cmd += f" {arguments['policy_set']}"
        if arguments.get("policy_name"):
            cmd += f" {arguments['policy_name']}"
        return self._execute_simple_query(cmd)
