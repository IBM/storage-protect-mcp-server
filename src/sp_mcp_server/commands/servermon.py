from typing import Any, Dict, List
from .base import BaseServermonCommand

class RunServerMon(BaseServermonCommand):
    @property
    def name(self) -> str:
        return "run_servermon"
    
    @property
    def required_privilege(self) -> str:
        return "operator"
    @property
    def description(self) -> str:
        return (
            "Runs the **Server Diagnostic Tool** (Servermon). This utility collects comprehensive system performance metrics, configuration data, and environment details for troubleshooting.\n"
            "**Behavior**:\n"
            "- If another servermon instance is running, this tool will automatically use the most recent diagnostics from the servermon XML directory (SP_SERVERMON_XML_DIR) instead of launching a new instance.\n"
            "- If no servermon is running, it launches a new instance with the specified arguments.\n"
            "**Input Parameters**:\n"
            "- args (Optional): List of specific arguments to customize data collection (e.g., ['-standard', '-dbonly']).\n"
            "**Output Parameters**:\n"
            "- Result: The raw output stream from the servermon utility or existing diagnostics if another instance is running.\n"
            "**Requirements**:\n"
            "- SP_SERVERMON_XML_DIR must be configured to use existing diagnostics when servermon is busy."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "args": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Arguments to pass to servermon."
                }
            }
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        args = arguments.get("args", [])
        return self._execute_servermon(args)
