from typing import Any, Dict
from ..base import BaseCommand

class DefineDataMover(BaseCommand):
    @property
    def name(self) -> str:
        return "define_data_mover"
        
    @property
    def description(self) -> str:
        return (
            "- Description: Defines a **Data Mover** in IBM Storage Protect. Used for NDMP backup operations with NAS file servers.\n"
            "**Input Parameters**:\n"
            "- name (Required): Name of the data mover. Must match a previously registered node name (REGISTER NODE TYPE=NAS). Maximum 64 characters.\n"
            "- type (Optional): Type of data mover. Default: NAS. Options:\n"
            "  - NAS: Standard NAS file server\n"
            "  - NASCLUSTER: Clustered NAS file server (AIX/Linux/Windows only, requires DATAFORMAT=NETAPPDUMP)\n"
            "  - NASVSERVER: Virtual storage device within a cluster (AIX/Linux/Windows only, requires DATAFORMAT=NETAPPDUMP)\n"
            "- hl_address (Required): High-level address - numerical IP address or domain name to access the NAS file server.\n"
            "- ll_address (Optional): Low-level address - TCP port number for NDMP sessions. Default: 10000.\n"
            "- data_format (Required): Data format used by the data mover:\n"
            "  - NETAPPDump: For NetApp NAS file servers and IBM System Storage N Series\n"
            "  - CELERRADump: For EMC Celerra NAS file servers\n"
            "  - NDMPDump: For other NAS file servers\n"
            "- user_id (Required): User ID authorized to initiate NDMP sessions with the NAS file server.\n"
            "- password (Required): Password for the user ID to log on to the NAS file server.\n"
            "- online (Optional): Whether the data mover is available for use. Default: Yes. Options: Yes, No.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the Data Mover was defined."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string", 
                    "description": "Data mover name (must match a registered NAS node name, max 64 characters)."
                },
                "type": {
                    "type": "string", 
                    "description": "Type of data mover: NAS (default), NASCLUSTER, or NASVSERVER.", 
                    "enum": ["NAS", "NASCLUSTER", "NASVSERVER"],
                    "default": "NAS"
                },
                "hl_address": {
                    "type": "string", 
                    "description": "High-level address: IP address or domain name of the NAS file server."
                },
                "ll_address": {
                    "type": "string", 
                    "description": "Low-level address: TCP port number for NDMP sessions (default: 10000)."
                },
                "data_format": {
                    "type": "string", 
                    "description": "Data format: NETAPPDump (NetApp/IBM N Series), CELERRADump (EMC Celerra), or NDMPDump (other NAS).", 
                    "enum": ["NETAPPDump", "CELERRADump", "NDMPDump"]
                },
                "user_id": {
                    "type": "string", 
                    "description": "User ID authorized for NDMP sessions with the NAS file server."
                },
                "password": {
                    "type": "string", 
                    "description": "Password for the user ID."
                },
                "online": {
                    "type": "string", 
                    "description": "Whether the data mover is available for use: Yes (default) or No.", 
                    "enum": ["Yes", "No"]
                }
            },
            "required": ["name", "hl_address", "data_format", "user_id", "password"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE DATAMOVER {arguments['name']}"
        
        # Add TYPE parameter (default is NAS if not specified)
        data_mover_type = arguments.get("type", "NAS")
        cmd += f" TYPE={data_mover_type}"
            
        # Add required HLADDRESS
        cmd += f" HLADDRESS={arguments['hl_address']}"
        
        # Add optional LLADDRESS (default is 10000)
        if arguments.get("ll_address"):
            cmd += f" LLADDRESS={arguments['ll_address']}"
            
        # Add required DATAFORMAT
        cmd += f" DATAFORMAT={arguments['data_format']}"
        
        # Add required USERID and PASSWORD
        cmd += f" USERID={arguments['user_id']} PASSWORD=\"{arguments['password']}\""
        
        # Add optional ONLINE parameter (default is Yes)
        if arguments.get("online"):
            cmd += f" ONLINE={arguments['online']}"
            
        return self._execute_simple_query(cmd)

class UpdateDataMover(BaseCommand):
    @property
    def name(self) -> str:
        return "update_data_mover"
    
    @property
    def description(self) -> str:
        return (
            "- Description: Updates a **Data Mover** configuration in IBM Storage Protect.\n"
            "**Input Parameters**:\n"
            "- name (Required): The data mover name to update.\n"
            "- type (Optional): Type of data mover: NAS, NASCLUSTER, or NASVSERVER.\n"
            "- hl_address (Optional): High-level address - IP address or domain name of the NAS file server.\n"
            "- ll_address (Optional): Low-level address - TCP port number for NDMP sessions.\n"
            "- data_format (Optional): Data format: NETAPPDump, CELERRADump, or NDMPDump.\n"
            "- user_id (Optional): User ID authorized for NDMP sessions.\n"
            "- password (Optional): Password for the user ID.\n"
            "- online (Optional): Whether the data mover is available for use: Yes or No.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the data mover was updated."
        )
    
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {
                    "type": "string", 
                    "description": "Data mover name to update."
                },
                "type": {
                    "type": "string", 
                    "description": "Type of data mover: NAS, NASCLUSTER, or NASVSERVER.", 
                    "enum": ["NAS", "NASCLUSTER", "NASVSERVER"]
                },
                "hl_address": {
                    "type": "string", 
                    "description": "High-level address: IP address or domain name."
                },
                "ll_address": {
                    "type": "string", 
                    "description": "Low-level address: TCP port number."
                },
                "data_format": {
                    "type": "string", 
                    "description": "Data format: NETAPPDump, CELERRADump, or NDMPDump.", 
                    "enum": ["NETAPPDump", "CELERRADump", "NDMPDump"]
                },
                "user_id": {
                    "type": "string", 
                    "description": "User ID for authentication."
                },
                "password": {
                    "type": "string", 
                    "description": "Password for authentication."
                },
                "online": {
                    "type": "string", 
                    "description": "Availability status: Yes or No.", 
                    "enum": ["Yes", "No"]
                }
            },
            "required": ["name"]
        }
    
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE DATAMOVER {arguments['name']}"
        
        if arguments.get("type"):
            cmd += f" TYPE={arguments['type']}"
        if arguments.get("hl_address"):
            cmd += f" HLADDRESS={arguments['hl_address']}"
        if arguments.get("ll_address"):
            cmd += f" LLADDRESS={arguments['ll_address']}"
        if arguments.get("data_format"):
            cmd += f" DATAFORMAT={arguments['data_format']}"
        if arguments.get("user_id"):
            cmd += f" USERID={arguments['user_id']}"
        if arguments.get("password"):
            cmd += f" PASSWORD=\"{arguments['password']}\""
        if arguments.get("online"):
            cmd += f" ONLINE={arguments['online']}"
            
        return self._execute_simple_query(cmd)

class DeleteDataMover(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_data_mover"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Data Mover** definition.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- mover_name (Required): The name of the data mover to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the data mover was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Mover name."}
            },
            "required": ["name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE DATAMOVER {arguments['name']}")

class QueryDataMover(BaseCommand):
    @property
    def name(self) -> str:
        return "query_data_mover"

    @property
    def description(self) -> str:
        return (
            "- Description: Display definitions for data movers (e.g., for NAS backup).\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- name (Optional): Data mover name.\n"
            "**Output Parameters**:\n"
            "- Data Mover Name: Name of the mover.\n"
            "- Type: Type of mover (e.g., NAS).\n"
            "- IP Address: Network address."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "name": {"type": "string", "description": "Data mover name."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY DATAMOVER"
        if arguments.get("name"):
            cmd += f" {arguments['name']}"
        return self._execute_simple_query(cmd)
