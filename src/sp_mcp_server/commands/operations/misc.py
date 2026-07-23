from typing import Any, Dict
from ..base import BaseCommand

__all__ = [
    'DefineScratchPadEntry',
    'UpdateScratchPadEntry',
    'DeleteScratchPadEntry',
    'QueryActivityLog',
    'QueryPendingCommand',
    'QueryProfile',
    'QueryUserRequest',
    'UpdateCollocationGroup'
]


class DefineScratchPadEntry(BaseCommand):
    @property
    def name(self) -> str:
        return "define_scratch_pad_entry"
    @property
    def description(self) -> str:
        return (
            "Define a **Scratch Pad Entry** (administrator note) for a specific object or purpose.\n"
            "**Input Parameters**:\n"
            "- object (Required): The name of the object to attach the note to.\n"
            "- message (Required): The content of the note.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the entry was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object": {"type": "string", "description": "Object name."},
                "message": {"type": "string", "description": "Message text."}
            },
            "required": ["object", "message"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DEFINE SCRATCHPADENTRY {arguments['object']} DESCRIPTION=\"{arguments['message']}\"")

class UpdateScratchPadEntry(BaseCommand):
    @property
    def name(self) -> str:
        return "update_scratch_pad_entry"
    @property
    def description(self) -> str:
        return (
            "Updates a **Scratch Pad** entry (administrator note).\n"
            "**Input Parameters**:\n"
            "- object (Required): The object name associated with the note.\n"
            "- message (Required): The new message/description.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the entry was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object": {"type": "string", "description": "Object name."},
                "message": {"type": "string", "description": "New message."}
            },
            "required": ["object", "message"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
         return self._execute_simple_query(f"UPDATE SCRATCHPADENTRY {arguments['object']} DESCRIPTION=\"{arguments['message']}\"")

class DeleteScratchPadEntry(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_scratch_pad_entry"
    @property
    def description(self) -> str:
        return (
            "Deletes a **Scratch Pad** entry.\n"
            "**Input Parameters**:\n"
            "- object (Required): The object name associated with the note.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the entry was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "object": {"type": "string", "description": "Object name."}
            },
            "required": ["object"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE SCRATCHPADENTRY {arguments['object']}")

class QueryActivityLog(BaseCommand):
    @property
    def name(self) -> str:
        return "query_activity_log"

    @property
    def description(self) -> str:
        return (
            "Display messages from the server activity/audit log using QUERY ACTLOG command.\n\n"
            "**IBM SP Command**: QUERY ACTLOG\n"
            "**Purpose**: Search the activity log for administrative commands, system messages, and audit events.\n\n"
            "**IMPORTANT - Avoid Large Result Sets**:\n"
            "Activity logs can be very large. ALWAYS use SEARCH parameter with date filters to avoid 'context condensed' errors.\n"
            "Without filters, queries may return thousands of messages causing response truncation.\n\n"
            "**Best Practices for Targeted Queries**:\n"
            "- Critical errors (last 24h): SEARCH=ANE* BEGINDATE=<yesterday>\n"
            "- DB backup failures (last 3 days): SEARCH=ANR2968E BEGINDATE=<3-days-ago>\n"
            "- Server errors (last 2 days): SEARCH=ANR0551E BEGINDATE=<2-days-ago>\n"
            "- Storage warnings (if needed): SEARCH=ANR1* BEGINDATE=<yesterday>\n"
            "- Specific node activity: SEARCH=<nodename> BEGINDATE=<date>\n\n"
            "**Input Parameters**:\n"
            "- search (Optional but RECOMMENDED): Search string to filter messages (e.g., ANR*, ANE*, message ID, node name).\n"
            "- begindate (Optional but RECOMMENDED): Start date (e.g. 2024-01-15 or MM/DD/YYYY).\n"
            "- enddate (Optional): End date (e.g. 2024-01-20 or MM/DD/YYYY).\n"
            "- begintime (Optional): Start time (e.g. 08:00).\n"
            "- endtime (Optional): End time (e.g. 18:00).\n\n"
            "**Output Parameters**:\n"
            "- Date/Time: When the event occurred.\n"
            "- Message: The log message content.\n"
            "- Severity: Level of importance (Info, Warning, Error).\n\n"
            "**Note**: For scheduled event status, use 'query_scheduled_event' tool instead (QUERY EVENT)."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Search string to filter messages."},
                "begindate": {"type": "string", "description": "Start date (e.g. 2024-01-15 or MM/DD/YYYY)."},
                "enddate": {"type": "string", "description": "End date (e.g. 2024-01-20 or MM/DD/YYYY)."},
                "begintime": {"type": "string", "description": "Start time (e.g. 08:00)."},
                "endtime": {"type": "string", "description": "End time (e.g. 18:00)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY ACTLOG"
        if arguments.get("search"):
            cmd += f" SEARCH={arguments['search']}"
        if arguments.get("begindate"):
            cmd += f" BEGINDATE={arguments['begindate']}"
        if arguments.get("enddate"):
            cmd += f" ENDDATE={arguments['enddate']}"
        if arguments.get("begintime"):
            cmd += f" BEGINTIME={arguments['begintime']}"
        if arguments.get("endtime"):
            cmd += f" ENDTIME={arguments['endtime']}"
        return self._execute_simple_query(cmd)

class QueryPendingCommand(BaseCommand):
    @property
    def name(self) -> str:
        return "query_pending_command"

    @property
    def description(self) -> str:
        return (
            "Display a list of administrative commands that are pending approval.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Command ID: ID to approve/reject.\n"
            "- Command: The command string.\n"
            "- Requestor: Who requested it."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY PENDINGCMD")

class QueryProfile(BaseCommand):
    @property
    def name(self) -> str:
        return "query_profile"

    @property
    def description(self) -> str:
        return (
            "Display information about profiles and associated objects.\n\n"
            "**⚠️ IMPORTANT**: This command must be issued from a **configuration manager** "
            "or a **managed server** with a configuration manager defined. "
            "It will fail with ANR3007E on standard standalone backup servers.\n\n"
            "**Input Parameters**:\n"
            "- server_name (Required): Configuration manager server name (SERVER=).\n"
            "- profile_name (Optional): Filter to a specific profile name.\n\n"
            "**Output Parameters**:\n"
            "- Profile Name: Name of the profile.\n"
            "- Description: Description of contents."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "server_name": {"type": "string", "description": "Configuration manager server name (required). Passed as SERVER=<name>."},
                "profile_name": {"type": "string", "description": "Profile name to filter results (optional)."}
            },
            "required": ["server_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY PROFILE"
        if arguments.get("profile_name"):
            cmd += f" {arguments['profile_name']}"
        cmd += f" SERVER={arguments['server_name']}"
        return self._execute_simple_query(cmd)

class QueryUserRequest(BaseCommand):
    @property
    def name(self) -> str:
        return "query_user_request"

    @property
    def description(self) -> str:
        return (
            "Query one or more pending manual mount requests (e.g., for tape).\n\n"
            "**Input Parameters**:\n"
            "- request_id (Optional): Request ID.\n\n"
            "**Output Parameters**:\n"
            "- Request ID: ID of the request.\n"
            "- Volume Name: Media required.\n"
            "- Drive Name: Drive to load."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                 "request_id": {"type": "string", "description": "Request ID."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY REQUEST"
        if arguments.get("request_id"):
             cmd += f" {arguments['request_id']}"
        return self._execute_simple_query(cmd)

class UpdateCollocationGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "update_collocation_group"
    @property
    def description(self) -> str:
        return (
            "Updates a **Collocation Group** description.\n"
            "**Input Parameters**:\n"
            "- group_name (Required): The group name.\n"
            "- description (Optional): The new description.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the group was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_name": {"type": "string", "description": "Group name."},
                "description": {"type": "string", "description": "Description."}
            },
            "required": ["group_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE COLLOCGROUP {arguments['group_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        return self._execute_simple_query(cmd)
