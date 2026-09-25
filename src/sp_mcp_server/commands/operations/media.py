from typing import Any, Dict
from ..base import BaseCommand

class DefineRecoveryMedia(BaseCommand):
    @property
    def name(self) -> str:
        return "define_recovery_media"
    @property
    def required_privilege(self) -> str:
        return "operator"
    @property
    def description(self) -> str:
        return (
            "Define **Recovery Media** information for disaster recovery. Records details about media containing system recovery data.\n"
            "**Input Parameters**:\n"
            "- media_name (Required): The name of the recovery media (max 30 chars).\n"
            "- volume_names (Optional): Comma-separated list of volume names associated with this media.\n"
            "- description (Optional): Description of the media contents.\n"
            "- location (Optional): Physical location of the media.\n"
            "- media_type (Optional): Type of media. Valid values: BOOT, OTHER. Default: OTHER.\n"
            "- product (Optional): Product name associated with the media.\n"
            "- product_info (Optional): Additional product information.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the media was defined."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "media_name": {"type": "string", "description": "Recovery media name (max 30 characters)."},
                "volume_names": {"type": "string", "description": "Comma-separated list of volume names."},
                "description": {"type": "string", "description": "Description of media contents."},
                "location": {"type": "string", "description": "Physical location of the media."},
                "media_type": {"type": "string", "enum": ["BOOT", "OTHER"], "description": "Type of media. Default: OTHER."},
                "product": {"type": "string", "description": "Product name."},
                "product_info": {"type": "string", "description": "Additional product information."}
            },
            "required": ["media_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE RECOVERYMEDIA {arguments['media_name']}"
        if arguments.get("volume_names"):
            cmd += f" VOLUMENAMES=\"{arguments['volume_names']}\""
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        if arguments.get("location"):
            cmd += f" LOCATION=\"{arguments['location']}\""
        if arguments.get("media_type"):
            cmd += f" TYPE={arguments['media_type']}"
        if arguments.get("product"):
            cmd += f" PRODUCT=\"{arguments['product']}\""
        if arguments.get("product_info"):
            cmd += f" PRODUCTINFO=\"{arguments['product_info']}\""
        return self._execute_simple_query(cmd)

class UpdateRecoveryMedia(BaseCommand):
    @property
    def name(self) -> str:
        return "update_recovery_media"
    @property
    def required_privilege(self) -> str:
        return "operator"
    @property
    def description(self) -> str:
        return (
            "Updates **Recovery Media** information.\n"
            "**Input Parameters**:\n"
            "- media_name (Required): The recovery media name.\n"
            "- volume_names (Optional): New comma-separated list of volume names.\n"
            "- description (Optional): New description.\n"
            "- location (Optional): New physical location.\n"
            "- media_type (Optional): New media type. Valid values: BOOT, OTHER.\n"
            "- product (Optional): New product name.\n"
            "- product_info (Optional): New product information.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the media was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "media_name": {"type": "string", "description": "Recovery media name."},
                "volume_names": {"type": "string", "description": "Comma-separated list of volume names."},
                "description": {"type": "string", "description": "Description of media contents."},
                "location": {"type": "string", "description": "Physical location."},
                "media_type": {"type": "string", "enum": ["BOOT", "OTHER"], "description": "Type of media."},
                "product": {"type": "string", "description": "Product name."},
                "product_info": {"type": "string", "description": "Product information."}
            },
            "required": ["media_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE RECOVERYMEDIA {arguments['media_name']}"
        if arguments.get("volume_names"):
            cmd += f" VOLUMENAMES=\"{arguments['volume_names']}\""
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        if arguments.get("location"):
            cmd += f" LOCATION=\"{arguments['location']}\""
        if arguments.get("media_type"):
            cmd += f" TYPE={arguments['media_type']}"
        if arguments.get("product"):
            cmd += f" PRODUCT=\"{arguments['product']}\""
        if arguments.get("product_info"):
            cmd += f" PRODUCTINFO=\"{arguments['product_info']}\""
        return self._execute_simple_query(cmd)

class DeleteRecoveryMedia(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_recovery_media"
    @property
    def required_privilege(self) -> str:
        return "operator"
    @property
    def description(self) -> str:
        return (
            "Deletes **Recovery Media** information.\n"
            "**Input Parameters**:\n"
            "- media_name (Required): The recovery media name.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the media was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "media_name": {"type": "string", "description": "Recovery media name."}
            },
            "required": ["media_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE RECOVERYMEDIA {arguments['media_name']}")
