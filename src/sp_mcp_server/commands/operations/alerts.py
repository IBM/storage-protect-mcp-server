from typing import Any, Dict
from ..base import BaseCommand

class DefineAlertTrigger(BaseCommand):
    @property
    def name(self) -> str:
        return "define_alert_trigger"
    @property
    def description(self) -> str:
        return (
            "Define an alert trigger with specific threshold.\n"
            "**Input Parameters**:\n"
            "- message_number (Required): Message number to trigger on. Max 8 characters.\n"
            "- category (Optional): Alert category. Valid: APplication, INventory, CLient, DEvice, OBjectclient, SErver, STorage, SYstems, VMclient. Default: SErver.\n"
            "- admin (Optional): Administrator name to receive email notification.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the trigger was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_number": {"type": "integer", "description": "Message number to associate with the alert trigger. Max 8 characters."},
                "category": {
                    "type": "string", 
                    "description": "Category type for the alert. Default: SErver.",
                    "enum": ["APplication", "INventory", "CLient", "DEvice", "OBjectclient", "SErver", "STorage", "SYstems", "VMclient"]
                },
                "admin": {"type": "string", "description": "Administrator name to receive email notification of this alert."}
            },
            "required": ["message_number"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE ALERTTRIGGER {arguments['message_number']}"
        if arguments.get("category"): cmd += f" CATegory={arguments['category']}"
        if arguments.get("admin"): cmd += f" ADmin={arguments['admin']}"
        return self._execute_simple_query(cmd)

class UpdateAlertTrigger(BaseCommand):
    @property
    def name(self) -> str:
        return "update_alert_trigger"
    @property
    def description(self) -> str:
        return (
            "Updates a defined **Alert Trigger**. Can modify category or manage admin notifications.\n"
            "**Input Parameters**:\n"
            "- message_number (Required): The message number identifying the alert.\n"
            "- category (Optional): New category. Valid: APplication, INventory, CLient, DEvice, OBjectclient, SErver, STorage, SYstems, VMclient.\n"
            "- addadmin (Optional): Administrator name(s) to add to email notification list. Comma-separated, no spaces.\n"
            "- deladmin (Optional): Administrator name(s) to remove from email notification list. Comma-separated, no spaces.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the trigger was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_number": {"type": "integer", "description": "Message number of the alert trigger to update. Max 8 characters."},
                "category": {
                    "type": "string", 
                    "description": "New category type for the alert.",
                    "enum": ["APplication", "INventory", "CLient", "DEvice", "OBjectclient", "SErver", "STorage", "SYstems", "VMclient"]
                },
                "addadmin": {"type": "string", "description": "Administrator name(s) to add to email notification list. Comma-separated, no spaces."},
                "deladmin": {"type": "string", "description": "Administrator name(s) to remove from email notification list. Comma-separated, no spaces."}
            },
            "required": ["message_number"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE ALERTTRIGGER {arguments['message_number']}"
        if arguments.get("category"): cmd += f" CATegory={arguments['category']}"
        if arguments.get("addadmin"): cmd += f" ADDadmin={arguments['addadmin']}"
        if arguments.get("deladmin"): cmd += f" DELadmin={arguments['deladmin']}"
        return self._execute_simple_query(cmd)

class UpdateAlertStatus(BaseCommand):
    @property
    def name(self) -> str:
        return "update_alert_status"
    @property
    def description(self) -> str:
        return (
            "Updates the status of an existing **Alert**.\n"
            "**Input Parameters**:\n"
            "- alert_id (Required): The unique ID of the alert.\n"
            "- status (Required): New status (e.g., CLOSED).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the alert status was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "alert_id": {"type": "integer", "description": "Alert ID."},
                "status": {"type": "string", "description": "New status."}
            },
            "required": ["alert_id", "status"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"UPDATE ALERTSTATUS {arguments['alert_id']} STATUS={arguments['status']}")

class DeleteAlertTrigger(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_alert_trigger"
    @property
    def description(self) -> str:
        return (
            "Deletes a defined **Alert Trigger**.\n"
            "**Input Parameters**:\n"
            "- message_number (Required): The message number to remove.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the trigger was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "message_number": {"type": "integer", "description": "Message number."}
            },
            "required": ["message_number"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE ALERTTRIGGER {arguments['message_number']}")

class QueryAlertTrigger(BaseCommand):
    @property
    def name(self) -> str:
        return "query_alert_trigger"

    @property
    def description(self) -> str:
        return (
            "Query the list of defined alert triggers that generate notifications.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Message Number: ID of the message triggering the alert.\n"
            "- Source: Origin of the alert."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY ALERTTRIGGER")

class QueryAlertStatus(BaseCommand):
    @property
    def name(self) -> str:
        return "query_alert_status"

    @property
    def description(self) -> str:
        return (
            "Query the current status of alerts in the system.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Alert ID: Unique ID.\n"
            "- Status: Active/Closed.\n"
            "- Message: Alert details."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY ALERTSTATUS")
