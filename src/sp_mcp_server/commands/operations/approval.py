from typing import Any, Dict
import logging
from ..base import BaseCommand

logger = logging.getLogger(__name__)

__all__ = [
    "ApprovePendingCmd",
    "RejectPendingCmd",
    "WithdrawPendingCmd",
]


class ApprovePendingCmd(BaseCommand):
    """Approve a command pending command-approval review (POL-1)."""

    @property
    def name(self) -> str:
        return "approve_pending_command"

    @property
    def required_privilege(self) -> str:
        # Any admin designated as CMDAPPROVER=YES can approve.
        # The system account (mcp-svc-system) carries this designation.
        return "system"

    @property
    def description(self) -> str:
        return (
            "Approve a **Pending Administrative Command** that is awaiting "
            "command-approval review.\n\n"
            "Use `query_pending_command` to list commands awaiting approval "
            "and obtain their Command ID.\n\n"
            "**Prerequisites**: IBM SP command approval must be enabled on the server:\n"
            "  SET COMMANDAPPROVAL ON\n"
            "  UPDATE ADMIN mcp-svc-system CMDAPPROVER=YES\n\n"
            "**Input Parameters**:\n"
            "- command_id (Required): The numeric ID of the pending command "
            "(from QUERY PENDINGCMD).\n\n"
            "**Output Parameters**:\n"
            "- Result: Confirmation that the command was approved and will now execute."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command_id": {
                    "type": "string",
                    "description": "The numeric ID of the pending command (from QUERY PENDINGCMD)."
                }
            },
            "required": ["command_id"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd_id = arguments["command_id"].strip()
        logger.warning(
            "POL-1: Approving pending command ID=%s via MCP tool 'approve_pending_command'",
            cmd_id,
        )
        return self._execute_simple_query(f"APPROVE PENDINGCMD {cmd_id}")


class RejectPendingCmd(BaseCommand):
    """Reject a command pending command-approval review (POL-1)."""

    @property
    def name(self) -> str:
        return "reject_pending_command"

    @property
    def required_privilege(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return (
            "Reject a **Pending Administrative Command** that is awaiting "
            "command-approval review. The command will NOT execute.\n\n"
            "Use `query_pending_command` to list commands and obtain their Command ID.\n\n"
            "**Input Parameters**:\n"
            "- command_id (Required): The numeric ID of the pending command "
            "(from QUERY PENDINGCMD).\n\n"
            "**Output Parameters**:\n"
            "- Result: Confirmation that the command was rejected."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command_id": {
                    "type": "string",
                    "description": "The numeric ID of the pending command (from QUERY PENDINGCMD)."
                }
            },
            "required": ["command_id"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd_id = arguments["command_id"].strip()
        logger.warning(
            "POL-1: Rejecting pending command ID=%s via MCP tool 'reject_pending_command'",
            cmd_id,
        )
        return self._execute_simple_query(f"REJECT PENDINGCMD {cmd_id}")


class WithdrawPendingCmd(BaseCommand):
    """Withdraw a pending command issued by the current administrator (POL-1)."""

    @property
    def name(self) -> str:
        return "withdraw_pending_command"

    @property
    def required_privilege(self) -> str:
        # The issuing admin can withdraw their own pending command without special privileges.
        return "any"

    @property
    def description(self) -> str:
        return (
            "Withdraw a **Pending Administrative Command** that was previously "
            "issued by the current administrator and has not yet been approved.\n\n"
            "**Input Parameters**:\n"
            "- command_id (Required): The numeric ID of the pending command.\n\n"
            "**Output Parameters**:\n"
            "- Result: Confirmation that the command was withdrawn."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "command_id": {
                    "type": "string",
                    "description": "The numeric ID of the pending command."
                }
            },
            "required": ["command_id"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd_id = arguments["command_id"].strip()
        logger.info(
            "POL-1: Withdrawing pending command ID=%s via MCP tool 'withdraw_pending_command'",
            cmd_id,
        )
        return self._execute_simple_query(f"WITHDRAW PENDINGCMD {cmd_id}")
