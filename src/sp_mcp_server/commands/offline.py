from typing import Any, Dict
from .base import BaseOfflineCommand

class QueryOfflineDBSpace(BaseOfflineCommand):
    @property
    def name(self) -> str:
        return "query_offline_db_space"

    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "Displays **Catalog** (Database) storage space information strictly in offline mode. The Catalog tracks all system metadata.\n"
            "**Input Parameters**:\n"
            "- None.\n"
            "**Output Parameters**:\n"
            "- Location: Directory paths for Catalog storage.\n"
            "- Capacity: Total storage capacity.\n"
            "- Used: Space currently utilized."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_utility("DISPLAY DBSPACE")

class QueryOfflineLog(BaseOfflineCommand):
    @property
    def name(self) -> str:
        return "query_offline_log"

    @property
    def required_privilege(self) -> str:
        return "system"
    @property
    def description(self) -> str:
        return (
            "Displays **Transaction Log** (Recovery Log) information strictly in offline mode. The log captures all active changes to the Catalog.\n"
            "**Input Parameters**:\n"
            "- None.\n"
            "**Output Parameters**:\n"
            "- Log Directories: Paths for Active, Archive, and Failover logs.\n"
            "- Space Utilization: Current usage metrics for the logs."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {}
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_utility("DISPLAY LOG")
