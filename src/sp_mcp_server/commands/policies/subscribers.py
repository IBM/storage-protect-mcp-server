from typing import Any, Dict
from ..base import BaseCommand

class QuerySubscriber(BaseCommand):
    @property
    def name(self) -> str:
        return "query_subscriber"

    @property
    def description(self) -> str:
        return (
            "Display information about subscribers and their profile subscriptions.\n\n"
            "**⚠️ IMPORTANT**: This command can only be issued on a **configuration manager** server.\n"
            "It will fail with ANR3000E on standard backup servers.\n\n"
            "**Input Parameters**:\n"
            "- server_name (Optional): Managed server name to query. Wildcards supported. Default: all servers.\n"
            "- profile_name (Optional): Filter by profile name (PROFIle=). Wildcards supported.\n\n"
            "**Output Parameters**:\n"
            "- Subscriber Name: Name of the managed server.\n"
            "- Profile: The subscribed profile."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "server_name": {"type": "string", "description": "Managed server name to query. Wildcards supported."},
                "profile_name": {"type": "string", "description": "Profile name filter (PROFIle=). Wildcards supported."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY SUBSCRIBER"
        if arguments.get("server_name"):
            cmd += f" {arguments['server_name']}"
        if arguments.get("profile_name"):
            cmd += f" PROFIle={arguments['profile_name']}"
        return self._execute_simple_query(cmd)

class QuerySubscription(BaseCommand):
    @property
    def name(self) -> str:
        return "query_subscription"

    @property
    def description(self) -> str:
        return (
            "Display subscription details, linking subscribers to specific profiles or services.\n\n"
            "**⚠️ IMPORTANT**: This command can only be issued on a **configuration manager** server.\n"
            "It will fail with ANR3000E on standard backup servers.\n\n"
            "**Input Parameters**:\n"
            "- subscription_name (Optional): Subscription name.\n\n"
            "**Output Parameters**:\n"
            "- Profile: The subscribed profile.\n"
            "- Administrator: The admin managing it."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "subscription_name": {"type": "string"}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY SUBSCRIPTION"
        if arguments.get("subscription_name"):
             cmd += f" {arguments['subscription_name']}"
        return self._execute_simple_query(cmd)
