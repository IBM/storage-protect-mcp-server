from typing import Any, Dict
from ..base import BaseCommand

class DefineCopyGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "define_copy_group"
    
    @property
    def description(self) -> str:
        return (
            "- Description: Defines a **Copy Group** that specifies exact retention parameters (e.g., how many versions to keep).\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Parent Policy Domain.\n"
            "- policy_set_name (Required): Parent Policy Set.\n"
            "- class_name (Required): Parent Management Class.\n"
            "- type (Required): 'BACKUP' or 'ARCHIVE' (Defaults to BACKUP).\n"
            "- destination (Required): The **Storage Pool** where data will be stored.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the rule was defined."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."},
                "class_name": {"type": "string", "description": "Management class name."},
                "type": {"type": "string", "enum": ["BACKUP", "ARCHIVE"], "default": "BACKUP", "description": "Type of copy group."},
                "destination": {"type": "string", "description": "Destination storage pool."},
                "verexists": {"type": "string", "description": "Versions data exists."},
                "verdeleted": {"type": "string", "description": "Versions data deleted."},
                "retextra": {"type": "string", "description": "Retain extra versions."},
                "retonly": {"type": "string", "description": "Retain only version."}
            },
            "required": ["domain_name", "policy_set_name", "class_name", "destination"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE COPYGROUP {arguments['domain_name']} {arguments['policy_set_name']} {arguments['class_name']} TYPE={arguments.get('type', 'BACKUP')} DESTINATION={arguments['destination']}"
        if arguments.get("verexists"):
            cmd += f" VEREXISTS={arguments['verexists']}"
        if arguments.get("verdeleted"):
            cmd += f" VERDELETED={arguments['verdeleted']}"
        if arguments.get("retextra"):
            cmd += f" RETEXTRA={arguments['retextra']}"
        if arguments.get("retonly"):
            cmd += f" RETONLY={arguments['retonly']}"
        return self._execute_simple_query(cmd)

class UpdateCopyGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "update_copy_group"
    @property
    def description(self) -> str:
        return (
            "- Description: Updates a **Copy Group** to modify retention parameters.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Parent Policy Domain.\n"
            "- policy_set_name (Required): Parent Policy Set.\n"
            "- class_name (Required): Parent Management Class.\n"
            "- type (Optional): 'BACKUP' or 'ARCHIVE' (Defaults to BACKUP).\n"
            "- destination (Optional): New Storage Pool.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the rule was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."},
                "class_name": {"type": "string", "description": "Class name."},
                "type": {"type": "string", "enum": ["BACKUP", "ARCHIVE"], "default": "BACKUP", "description": "Type."},
                "destination": {"type": "string", "description": "Destination pool."},
                "verexists": {"type": "string", "description": "Versions exists."},
                "verdeleted": {"type": "string", "description": "Versions deleted."},
                "retextra": {"type": "string", "description": "Retain extra."},
                "retonly": {"type": "string", "description": "Retain only."}
            },
            "required": ["domain_name", "policy_set_name", "class_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE COPYGROUP {arguments['domain_name']} {arguments['policy_set_name']} {arguments['class_name']} TYPE={arguments.get('type','BACKUP')}"
        if arguments.get("destination"): cmd += f" DESTINATION={arguments['destination']}"
        if arguments.get("verexists"): cmd += f" VEREXISTS={arguments['verexists']}"
        if arguments.get("verdeleted"): cmd += f" VERDELETED={arguments['verdeleted']}"
        if arguments.get("retextra"): cmd += f" RETEXTRA={arguments['retextra']}"
        if arguments.get("retonly"): cmd += f" RETONLY={arguments['retonly']}"
        return self._execute_simple_query(cmd)

class DeleteCopyGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_copy_group"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Copy Group**. This removes specific retention settings from a management class.\n"
            "**Input Parameters**:\n"
            "- domain_name (Required): Parent Policy Domain.\n"
            "- policy_set_name (Required): Parent Policy Set.\n"
            "- class_name (Required): Parent Management Class.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the rule was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "domain_name": {"type": "string", "description": "Domain name."},
                "policy_set_name": {"type": "string", "description": "Policy set name."},
                "class_name": {"type": "string", "description": "Class name."},
                "type": {"type": "string", "enum": ["BACKUP", "ARCHIVE"], "default": "BACKUP", "description": "Type."}
            },
            "required": ["domain_name", "policy_set_name", "class_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE COPYGROUP {arguments['domain_name']} {arguments['policy_set_name']} {arguments['class_name']} TYPE={arguments.get('type', 'BACKUP')}")

class QueryRetentionRuleConfig(BaseCommand):
    @property
    def name(self) -> str:
        return "query_retention_rule_config"

    @property
    def description(self) -> str:
        return (
            "- Description: Queries **Copy Groups**. Shows exact numeric values for retention limits.\n"
            "**Input Parameters**:\n"
            "- policy_group (Optional): Parent domain.\n"
            "- policy_set (Optional): Parent profile.\n"
            "- policy_name (Optional): Parent Management Class.\n"
            "**Output Parameters**:\n"
            "- Mgmt Class Name: Parent policy.\n"
            "- Copy Group Name: Rule identifier.\n"
            "- Versions Data Exists: Max versions retained.\n"
            "- Versions Data Deleted: Versions retained after deletion.\n"
            "- Retain Extra Versions: Days to keep inactive versions.\n"
            "- Retain Only Version: Days to keep final version."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "policy_group": {"type": "string"},
                "policy_set": {"type": "string"},
                "policy_name": {"type": "string", "description": "Protection policy name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY COPYGROUP"
        if arguments.get("policy_group"):
            cmd += f" {arguments['policy_group']}"
        if arguments.get("policy_set"):
            cmd += f" {arguments['policy_set']}"
        if arguments.get("policy_name"):
            cmd += f" {arguments['policy_name']}"
        return self._execute_simple_query(cmd)

class QuerySubRule(BaseCommand):
    @property
    def name(self) -> str:
        return "query_subrule"

    @property
    def description(self) -> str:
        return (
            "Display configuration for sub-file level frequency rules.\n\n"
            "**Input Parameters**:\n"
            "- parent_rule_name (Required): Name of the parent storage rule.\n"
            "- subrule_name (Optional): Name of the subrule to filter results (max 30 chars).\n"
            "- format (Optional): Output format: Standard, Detailed.\n\n"
            "**Output Parameters**:\n"
            "- Rule Name: Name of the subrule."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "parent_rule_name": {"type": "string", "description": "Name of the parent storage rule (required)."},
                "subrule_name": {"type": "string", "description": "Name of the subrule to filter results (optional, max 30 chars)."},
                "format": {"type": "string", "description": "Output format.", "enum": ["Standard", "Detailed"]}
            },
            "required": ["parent_rule_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"QUERY SUBRULE {arguments['parent_rule_name']}"
        if arguments.get("subrule_name"):
            cmd += f" {arguments['subrule_name']}"
        if arguments.get("format"):
            cmd += f" Format={arguments['format']}"
        return self._execute_simple_query(cmd)

class QueryRetentionRule(BaseCommand):
    @property
    def name(self) -> str:
        return "query_retention_rule"

    @property
    def description(self) -> str:
        return (
            "Query Copy Groups that define how long retention sets are kept.\n\n"
            "**Input Parameters**:\n"
            "- rule_name (Optional): Rule name.\n\n"
            "**Output Parameters**:\n"
            "- Rule Name: Name of the rule.\n"
            "- Retention Period: Duration to keep data.\n"
            "- Stack: Whether new data is stacked."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string"}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY RETRULE"
        if arguments.get("rule_name"):
             cmd += f" {arguments['rule_name']}"
        return self._execute_simple_query(cmd)

class QueryRetentionSet(BaseCommand):
    @property
    def name(self) -> str:
        return "query_retention_set"

    @property
    def description(self) -> str:
        return (
            "Query existence and status of retention sets (snapshots suitable for long-term retention).\n\n"
            "**Input Parameters**:\n"
            "- retset_id (Optional): Retention set ID.\n\n"
            "**Output Parameters**:\n"
            "- Retention Set ID: Unique ID.\n"
            "- Rule Name: The rule govenerning it.\n"
            "- Creation Date: Date created.\n"
            "- Expiration Date: When it expires."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                 "retset_id": {"type": "string", "description": "Retention set ID."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY RETSET"
        if arguments.get("retset_id"):
             cmd += f" {arguments['retset_id']}"
        return self._execute_simple_query(cmd)

class QueryRetentionSetContents(BaseCommand):
    @property
    def name(self) -> str:
        return "query_retention_set_contents"

    @property
    def description(self) -> str:
        return (
            "Query the detailed contents (files/objects) within a retention set.\n\n"
            "**IMPORTANT**: At least one of retset_id, node_name, or retention_rule_name is required. "
            "retset_id is mutually exclusive with node_name and retention_rule_name.\n\n"
            "**Input Parameters**:\n"
            "- retset_id (Optional): Unique numeric retention set ID. Mutually exclusive with node_name and retention_rule_name.\n"
            "- node_name (Optional): Node or node group name. Wildcards supported.\n"
            "- filespace_name (Optional): File space or virtual machine name. Only valid with node_name.\n"
            "- retention_rule_name (Optional): Retention rule name that triggered the set. Wildcards supported.\n"
            "- count (Optional): Number of files to display.\n"
            "- format (Optional): Output format: Standard, Detailed.\n\n"
            "**Output Parameters**:\n"
            "- File Name: Name of the file.\n"
            "- Size: File size."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "description": (
                "At least one of retset_id, node_name, or retention_rule_name is required. "
                "retset_id is mutually exclusive with node_name and retention_rule_name."
            ),
            "properties": {
                "retset_id": {
                    "type": "string",
                    "description": "Unique numeric retention set ID. Mutually exclusive with node_name and retention_rule_name."
                },
                "node_name": {
                    "type": "string",
                    "description": "Node or node group name (NOdename=). Wildcards supported."
                },
                "filespace_name": {
                    "type": "string",
                    "description": "File space or virtual machine name (FIlespace=). Only valid with node_name."
                },
                "retention_rule_name": {
                    "type": "string",
                    "description": "Retention rule name that triggered the set (RETRulename=). Wildcards supported."
                },
                "count": {
                    "type": "integer",
                    "description": "Number of files to display (COUnt=)."
                },
                "format": {
                    "type": "string",
                    "description": "Output format.",
                    "enum": ["Standard", "Detailed"]
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        if not any([arguments.get("retset_id"), arguments.get("node_name"), arguments.get("retention_rule_name")]):
            return "Error: At least one of retset_id, node_name, or retention_rule_name is required."
        cmd = "QUERY RETSETCONTENTS"
        if arguments.get("retset_id"):
            cmd += f" {arguments['retset_id']}"
        if arguments.get("node_name"):
            cmd += f" NOdename={arguments['node_name']}"
            if arguments.get("filespace_name"):
                cmd += f" FIlespace={arguments['filespace_name']}"
        if arguments.get("retention_rule_name"):
            cmd += f" RETRulename={arguments['retention_rule_name']}"
        if arguments.get("count"):
            cmd += f" COUnt={arguments['count']}"
        if arguments.get("format"):
            cmd += f" Format={arguments['format']}"
        return self._execute_simple_query(cmd)
