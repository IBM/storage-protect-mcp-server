from typing import Any, Dict
from ..base import BaseCommand

class QueryRecoveryLog(BaseCommand):
    @property
    def name(self) -> str:
        return "query_recovery_log"

    @property
    def description(self) -> str:
        return (
            "- Description: Display information about the transaction recovery log.\n\n"
            "**Input Parameters**:\n"
            "- format (Optional): Level of detail (standard, detailed).\n\n"
            "**Output Parameters**:\n"
            "- Total Space: Total size of the recovery log.\n"
            "- Used Space: Amount of log space currently in use.\n"
            "- Free Space: Remaining log space.\n"
            "- Log Pool Pct: Percentage of the log pool used."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "format": {
                    "type": "string",
                    "enum": ["standard", "detailed"],
                    "description": "Level of detail for the output.",
                    "default": "standard"
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        base_cmd = "QUERY LOG"
        if arguments.get("format") == "detailed":
            base_cmd += " FORMAT=DETAILED"
        return self._execute_simple_query(base_cmd)

class QueryEnabledEvents(BaseCommand):
    @property
    def name(self) -> str:
        return "query_enabled_events"

    @property
    def description(self) -> str:
        return (
            "- Description: Query which system events are currently enabled for logging or alerting.\n\n"
            "**Input Parameters**:\n"
            "- event_type (Required): Event type to query. Valid values: SCHEDULE, ACCOUNTING, THRESHOLD, REPLICATION, ALL.\n\n"
            "**Output Parameters**:\n"
            "- Event Name: The type of event.\n"
            "- Enabled: Whether the event is active.\n"
            "- Receiver: Where the event is sent (e.g., CONSOLE, ACTLOG)."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "event_type": {
                    "type": "string",
                    "description": "Event type to query (e.g., SCHEDULE, ACCOUNTING, THRESHOLD, REPLICATION, ALL).",
                    "enum": ["SCHEDULE", "ACCOUNTING", "THRESHOLD", "REPLICATION", "ALL"]
                }
            },
            "required": ["event_type"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"QUERY ENABLED {arguments['event_type']}")

class QueryEventRules(BaseCommand):
    @property
    def name(self) -> str:
        return "query_event_rules"

    @property
    def description(self) -> str:
        return (
            "- Description: Query configured event rules which filter or direct specific events.\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Rule Name: Name of the rule.\n"
            "- Description: What the rule does."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY EVENTRULES")

class QueryEventReceiver(BaseCommand):
    @property
    def name(self) -> str:
        return "query_event_receiver"

    @property
    def description(self) -> str:
        return (
            "- Description: Query configured event receivers (destinations for events).\n\n"
            "**Input Parameters**:\n"
            "- None.\n\n"
            "**Output Parameters**:\n"
            "- Receiver Name: Name of the receiver.\n"
            "- Description: Details about the receiver."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query("QUERY EVENTSERVER")
