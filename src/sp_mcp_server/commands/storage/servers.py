from typing import Any, Dict
from ..base import BaseCommand

class QueryTargetServer(BaseCommand):
    @property
    def name(self) -> str:
        return "query_target_server"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "- Description: Query the definitions of other backup servers known to this system.\n\n"
            "**Input Parameters**:\n"
            "- server_name (Optional): Name of the target server.\n\n"
            "**Output Parameters**:\n"
            "- Server Name: Name of the remote server.\n"
            "- Server Address: Network address.\n"
            "- Server Password Set: Indicates if a password is set."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "server_name": {"type": "string", "description": "Name of the target server."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY SERVER"
        if arguments.get("server_name"):
            cmd += f" {arguments['server_name']}"
        return self._execute_simple_query(cmd)

class QueryServerGroup(BaseCommand):
    @property
    def name(self) -> str:
        return "query_server_group"

    @property
    def required_privilege(self) -> str:
        return "any"
    @property
    def description(self) -> str:
        return (
            "- Description: Query server groups, which are collections of servers managed together.\n\n"
            "**Input Parameters**:\n"
            "- group_name (Optional): Name of the server group.\n\n"
            "**Output Parameters**:\n"
            "- Group Name: Name of the group.\n"
            "- Member Server: Servers belonging to the group."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "group_name": {"type": "string", "description": "Name of the server group."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY SERVERGROUP"
        if arguments.get("group_name"):
            cmd += f" {arguments['group_name']}"
        return self._execute_simple_query(cmd)
