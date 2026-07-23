from typing import Any, Dict
from ..base import BaseCommand

class DefineSpaceTrigger(BaseCommand):
    @property
    def name(self) -> str:
        return "define_space_trigger"
    @property
    def description(self) -> str:
        return (
            "Define a **Space Trigger** for a storage pool. Automatically expands the pool when space runs low.\n"
            "**Input Parameters**:\n"
            "- pool_name (Optional): The name of the storage pool. If omitted, applies to all pools.\n"
            "- full_pct (Optional): The utilization percentage to trigger expansion. Default: 80%.\n"
            "- space_expansion (Optional): The percentage to expand the pool by. Default: 20%.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the trigger was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name. If omitted, applies to all pools."},
                "full_pct": {"type": "integer", "description": "Full percentage threshold (default 80%)."},
                "space_expansion": {"type": "integer", "description": "Percentage to expand pool by (default 20%)."}
            },
            "required": []
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "DEFINE SPACETRIGGER STG"
        if arguments.get("full_pct") is not None:
            cmd += f" FULLPCT={arguments['full_pct']}"
        if arguments.get("space_expansion") is not None:
            cmd += f" SPACEEXPANSION={arguments['space_expansion']}"
        if arguments.get("pool_name"):
            cmd += f" STGPOOL={arguments['pool_name']}"
        return self._execute_simple_query(cmd)

class UpdateSpaceTrigger(BaseCommand):
    @property
    def name(self) -> str:
        return "update_space_trigger"
    @property
    def description(self) -> str:
        return (
            "Updates a **Space Trigger** for a storage pool.\n"
            "**Input Parameters**:\n"
            "- pool_name (Optional): The storage pool name. If omitted, updates global trigger.\n"
            "- full_pct (Optional): New full percentage threshold to trigger expansion.\n"
            "- space_expansion (Optional): New percentage to expand the pool by.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the trigger was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Pool name. If omitted, updates global trigger."},
                "full_pct": {"type": "integer", "description": "Full percentage threshold."},
                "space_expansion": {"type": "integer", "description": "Percentage to expand pool by."}
            },
            "required": []
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "UPDATE SPACETRIGGER STG"
        if arguments.get("full_pct") is not None:
            cmd += f" FULLPCT={arguments['full_pct']}"
        if arguments.get("space_expansion") is not None:
            cmd += f" SPACEEXPANSION={arguments['space_expansion']}"
        if arguments.get("pool_name"):
            cmd += f" STGPOOL={arguments['pool_name']}"
        return self._execute_simple_query(cmd)

class DeleteSpaceTrigger(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_space_trigger"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Space Trigger** from a storage pool.\n"
            "**Input Parameters**:\n"
            "- pool_name (Optional): The storage pool name. If omitted, deletes global trigger.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the trigger was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name. If omitted, deletes global trigger."}
            },
            "required": []
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "DELETE SPACETRIGGER STG"
        if arguments.get("pool_name"):
            cmd += f" STGPOOL={arguments['pool_name']}"
        return self._execute_simple_query(cmd)

class DefineStatusThreshold(BaseCommand):
    @property
    def name(self) -> str:
        return "define_status_threshold"
    @property
    def description(self) -> str:
        return (
            "Define a **Status Threshold** definition for system monitoring. Sets conditions for health reporting.\n"
            "**Input Parameters**:\n"
            "- threshold_name (Required): The name of the threshold (max 48 chars).\n"
            "- activity (Required): The system activity to monitor. Valid values: PROCESSSUMMARY, SESSIONSUMMARY, CLIENTSESSIONSUMMARY, SCHEDCLIENTSESSIONSUMMARY, DBUTIL, DBFREESPACE, DBUSEDSPACE, ARCHIVELOGFREESPACE, STGPOOLUTIL, STGPOOLCAPACITY, AVGSTGPOOLUTIL, TOTSTGPOOLCAPACITY, TOTSTGPOOLS, TOTRWSTGPOOLS, TOTNOTRWSTGPOOLS, STGPOOLINUSEANDDEFINED, ACTIVELOGUTIL, ARCHLOGUTIL, CPYSTGPOOLUTIL, PMRYSTGPOOLUTIL, DEVCLASSPCTDRVOFFLINE, DEVCLASSPCTDRVPOLLING, DEVCLASSPCTLIBPATHSOFFLINE, DEVCLASSPCTPATHSOFFLINE, DEVCLASSPCTDISKSUNAVAILABLE, FILEDEVCLASSPCTSCRUNALLOCATABLE.\n"
            "- condition (Optional): The condition to check. Valid values: GT, GE, LT, LE, EQual, EXists. Default: EXists.\n"
            "- value (Optional): The threshold value. Required for GT, GE, LT, LE, EQual conditions. Not used with EXists.\n"
            "- status (Optional): The status to report when threshold is met. Valid values: Normal, Warning, Error. Default: Normal.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the threshold was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "threshold_name": {"type": "string", "description": "Threshold name (max 48 characters)."},
                "activity": {"type": "string", "description": "Activity type. Valid values: PROCESSSUMMARY, SESSIONSUMMARY, CLIENTSESSIONSUMMARY, SCHEDCLIENTSESSIONSUMMARY, DBUTIL, DBFREESPACE, DBUSEDSPACE, ARCHIVELOGFREESPACE, STGPOOLUTIL, STGPOOLCAPACITY, AVGSTGPOOLUTIL, etc."},
                "condition": {"type": "string", "enum": ["GT", "GE", "LT", "LE", "EQual", "EXists"], "description": "Condition type. Default: EXists."},
                "value": {"type": "number", "description": "Threshold value. Required for GT, GE, LT, LE, EQual conditions."},
                "status": {"type": "string", "enum": ["Normal", "Warning", "Error"], "description": "Status to report. Default: Normal."}
            },
            "required": ["threshold_name", "activity"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE STATUSTHRESHOLD {arguments['threshold_name']} {arguments['activity']}"
        if arguments.get("condition"): 
            cmd += f" CONDITION={arguments['condition']}"
        if arguments.get("value") is not None: 
            cmd += f" VALUE={arguments['value']}"
        if arguments.get("status"): 
            cmd += f" STATUS={arguments['status']}"
        return self._execute_simple_query(cmd)

class UpdateStatusThreshold(BaseCommand):
    @property
    def name(self) -> str:
        return "update_status_threshold"
    @property
    def description(self) -> str:
        return (
            "Updates a **Status Threshold** definition for system monitoring.\n"
            "**Input Parameters**:\n"
            "- threshold_name (Required): The name of the threshold.\n"
            "- activity (Optional): The activity type to monitor.\n"
            "- condition (Optional): The condition type. Valid values: GT, GE, LT, LE, EQual, EXists.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the threshold was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "threshold_name": {"type": "string", "description": "Threshold name."},
                "activity": {"type": "string", "description": "Activity type."},
                "condition": {"type": "string", "enum": ["GT", "GE", "LT", "LE", "EQual", "EXists"], "description": "Condition type."}
            },
            "required": ["threshold_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE STATUSTHRESHOLD {arguments['threshold_name']}"
        if arguments.get("activity"): cmd += f" {arguments['activity']}"
        if arguments.get("condition"): cmd += f" CONDITION={arguments['condition']}"
        return self._execute_simple_query(cmd)

class DeleteStatusThreshold(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_status_threshold"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Status Threshold** definition.\n"
            "**Input Parameters**:\n"
            "- threshold_name (Required): The name of the threshold.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the threshold was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "threshold_name": {"type": "string", "description": "Threshold name."}
            },
            "required": ["threshold_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE STATUSTHRESHOLD {arguments['threshold_name']}")

class DefineStorageRule(BaseCommand):
    @property
    def name(self) -> str:
        return "define_storage_rule"
    @property
    def description(self) -> str:
        return (
            "Define a **Storage Rule** for tiering or auditing. Automates data movement between tiers.\n"
            "**Input Parameters**:\n"
            "- rule_name (Required): The name of the new storage rule.\n"
            "- target_name (Required): Target container or pool name.\n"
            "- action_type (Required): The action to perform. Valid: AUDit, GENdedupstats, REClaim, RETention, TIERBYAge, TIERBYState, NOTiering, COPY, NOCopying, REPLicate, NOREPLicating.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the rule was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Storage rule name."},
                "target_name": {"type": "string", "description": "Target container or pool name."},
                "action_type": {
                    "type": "string",
                    "description": "Action type for the rule.",
                    "enum": ["AUDit", "GENdedupstats", "REClaim", "RETention", "TIERBYAge",
                             "TIERBYState", "NOTiering", "COPY", "NOCopying", "REPLicate", "NOREPLicating"]
                }
            },
            "required": ["rule_name", "target_name", "action_type"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(
            f"DEFINE STGRULE {arguments['rule_name']} {arguments['target_name']} ACTIONTYPE={arguments['action_type']}"
        )

class UpdateStorageRule(BaseCommand):
    @property
    def name(self) -> str:
        return "update_storage_rule"
    @property
    def description(self) -> str:
        return (
            "Updates a **Storage Rule** (e.g., enable/disable).\n"
            "**Input Parameters**:\n"
            "- rule_name (Required): The rule name.\n"
            "- active (Optional): 'YES' or 'NO' to activate/deactivate the rule.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the rule was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Rule name."},
                "active": {"type": "string", "enum": ["YES", "NO"], "description": "Active status."}
            },
            "required": ["rule_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE STGRULE {arguments['rule_name']}"
        if arguments.get("active"): cmd += f" ACTIVE={arguments['active']}"
        return self._execute_simple_query(cmd)

class DeleteStorageRule(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_storage_rule"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Storage Rule**.\n"
            "**Input Parameters**:\n"
            "- rule_name (Required): The rule name.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the rule was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Rule name."}
            },
            "required": ["rule_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE STGRULE {arguments['rule_name']}")

class DefineSubRule(BaseCommand):
    @property
    def name(self) -> str:
        return "define_sub_rule"
    @property
    def description(self) -> str:
        return (
            "Define a **Subrule** for a storage rule. Adds specific targets to a parent rule.\n"
            "**Input Parameters**:\n"
            "- rule_name (Required): The parent storage rule name.\n"
            "- sub_rule_name (Required): The name of the subrule.\n"
            "- target_name (Optional): The target entity (e.g., node group).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the subrule was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Parent rule name."},
                "sub_rule_name": {"type": "string", "description": "Sub rule name."},
                "target_name": {"type": "string", "description": "Target entity name."}
            },
            "required": ["rule_name", "sub_rule_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE SUBRULE {arguments['rule_name']} {arguments['sub_rule_name']}"
        if arguments.get("target_name"): cmd += f" TARGETNAME={arguments['target_name']}"
        return self._execute_simple_query(cmd)

class UpdateSubRule(BaseCommand):
    @property
    def name(self) -> str:
        return "update_sub_rule"
    @property
    def description(self) -> str:
        return (
            "Updates a **Subrule** within a storage rule.\n"
            "**Input Parameters**:\n"
            "- rule_name (Required): The parent rule name.\n"
            "- sub_rule_name (Required): The subrule name.\n"
            "- target_name (Optional): New target entity name.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the subrule was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Rule name."},
                "sub_rule_name": {"type": "string", "description": "Sub rule name."},
                "target_name": {"type": "string", "description": "New target."}
            },
            "required": ["rule_name", "sub_rule_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE SUBRULE {arguments['rule_name']} {arguments['sub_rule_name']}"
        if arguments.get("target_name"): cmd += f" TARGETNAME={arguments['target_name']}"
        return self._execute_simple_query(cmd)

class DeleteSubRule(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_sub_rule"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Subrule** from a storage rule.\n"
            "**Input Parameters**:\n"
            "- rule_name (Required): The parent rule name.\n"
            "- sub_rule_name (Required): The subrule name.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the subrule was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "rule_name": {"type": "string", "description": "Rule name."},
                "sub_rule_name": {"type": "string", "description": "Sub rule name."}
            },
            "required": ["rule_name", "sub_rule_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE SUBRULE {arguments['rule_name']} {arguments['sub_rule_name']}")

class QueryStorageRule(BaseCommand):
    @property
    def name(self) -> str:
        return "query_storage_rule"

    @property
    def description(self) -> str:
        return (
            "Display information about storage rules (e.g., tiering rules).\n\n"
            "**Input Parameters**:\n"
            "- rule_name (Optional): Rule name.\n\n"
            "**Output Parameters**:\n"
            "- Rule Name: Name of the rule.\n"
            "- Source Pool: Source container.\n"
            "- Target Pool: Destination container."
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
        cmd = "QUERY STGRULE"
        if arguments.get("rule_name"):
             cmd += f" {arguments['rule_name']}"
        return self._execute_simple_query(cmd)
