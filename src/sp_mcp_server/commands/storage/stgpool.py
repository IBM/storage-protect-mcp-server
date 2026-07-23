from typing import Any, Dict
from ..base import BaseCommand

class DefineStoragePool(BaseCommand):
    @property
    def name(self) -> str:
        return "define_storage_pool"

    @property
    def description(self) -> str:
        return (
            "- Description: Defines a new **Storage Pool** (also referred to as a Container for certain pool types). This is a named resource consisting of multiple storage units (volumes) where backup data is stored.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- pool_name (Required): Name for the new Storage Pool.\n"
            "- device_class_name (Required): The **Device Class** determining the hardware type (e.g., LTO, DISK).\n"
            "- pool_type (Optional): The function of the pool ('PRIMARY', 'COPY', 'ACTIVE', 'CONTAINER').\n"
            "- description (Optional): Description of the target.\n"
            "- max_scratch (Optional): Maximum number of scratch volumes allowed.\n"
            "- reclaim (Optional): Threshold percentage to trigger space reclamation.\n"
            "- collocate (Optional): Collocation setting to group data (e.g., by Node or Group).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the Storage Pool was defined."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Name of the storage pool."},
                "device_class_name": {"type": "string", "description": "Name of the device class."},
                "pool_type": {
                    "type": "string", 
                    "enum": ["PRIMARY", "COPY", "ACTIVE", "CONTAINER"],
                    "default": "PRIMARY",
                    "description": "Type of storage pool."
                },
                "description": {"type": "string", "description": "Description of the pool."},
                "max_scratch": {"type": "integer", "description": "Maximum scratch volumes."},
                "reclaim": {"type": "integer", "description": "Reclamation threshold (0-100)."},
                "collocate": {
                    "type": "string",
                    "enum": ["NO", "GROUP", "NODE", "FILESPACE"],
                    "description": "Collocation setting."
                }
            },
            "required": ["pool_name", "device_class_name"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE STGPOOL {arguments['pool_name']} {arguments['device_class_name']}"
        if arguments.get("pool_type"):
            cmd += f" POOLTYPE={arguments['pool_type']}"
        if arguments.get("description"):
            cmd += f" DESCRIPTION=\"{arguments['description']}\""
        if arguments.get("max_scratch") is not None:
            cmd += f" MAXSCRATCH={arguments['max_scratch']}"
        if arguments.get("reclaim") is not None:
            cmd += f" RECLAIM={arguments['reclaim']}"
        if arguments.get("collocate"):
            cmd += f" COLLOCATE={arguments['collocate']}"
        
        return self._execute_simple_query(cmd)

class DefineStoragePoolDirectory(BaseCommand):
    @property
    def name(self) -> str:
        return "define_storage_pool_directory"
    
    @property
    def description(self) -> str:
        return (
            "- Description: Adds a filesystem directory to a **Container Storage Pool** (Storage Pool Directory) for deduplicated data storage.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- pool_name (Required): The name of the Container Storage Pool.\n"
            "- directory (Required): The absolute filesystem path to add.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the directory was added."
        )
        
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name."},
                "directory": {"type": "string", "description": "Directory path."}
            },
            "required": ["pool_name", "directory"]
        }
        
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"DEFINE STGPOOLDIRECTORY {arguments['pool_name']} \"{arguments['directory']}\""
        return self._execute_simple_query(cmd)

class UpdateStorageTarget(BaseCommand):
    @property
    def name(self) -> str:
        return "update_storage_target"
    @property
    def description(self) -> str:
        return (
            "- Description: Update a Storage Pool configuration. A storage pool is a named set of volumes used to store data.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- target_name (Required): Name of the storage pool to update.\n"
            "- description (Optional): New description for the pool.\n"
            "- max_scratch (Optional): Maximum number of scratch volumes allowed.\n"
            "- reclaim_threshold (Optional): Threshold percentage for space reclamation (0-100).\n"
            "- access_mode (Optional): One of 'READWRITE', 'READONLY', 'UNAVAILABLE', etc.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the pool was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_name": {"type": "string", "description": "Storage target name."},
                "description": {"type": "string", "description": "Description."},
                "max_scratch": {"type": "integer", "description": "Max scratch volumes."},
                "reclaim_threshold": {"type": "integer", "description": "Reclamation threshold (0-100)."},
                "access_mode": {"type": "string", "enum": ["READWRITE", "READONLY", "UNAVAILABLE"], "description": "Access mode."}
            },
            "required": ["target_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE STGPOOL {arguments['target_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        if arguments.get("max_scratch") is not None: cmd += f" MAXSCRATCH={arguments['max_scratch']}"
        if arguments.get("reclaim_threshold") is not None: cmd += f" RECLAIM={arguments['reclaim_threshold']}"
        if arguments.get("access_mode"): cmd += f" ACCESS={arguments['access_mode']}"
        return self._execute_simple_query(cmd)

class UpdateStoragePool(BaseCommand):
    @property
    def name(self) -> str:
        return "update_storage_pool"
    @property
    def description(self) -> str:
        return (
            "- Description: Update a storage pool.\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): Name of the storage pool to update.\n"
            "- description (Optional): New description.\n"
            "- max_scratch (Optional): New max scratch limit.\n"
            "- reclaim (Optional): New reclamation threshold.\n"
            "- accession (Optional): New access mode (READWRITE, READONLY, UNAVAILABLE, etc.).\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the pool was updated."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Storage pool name."},
                "description": {"type": "string", "description": "Description."},
                "max_scratch": {"type": "integer", "description": "Max scratch volumes."},
                "reclaim": {"type": "integer", "description": "Reclamation threshold."},
                "accession": {"type": "string", "enum": ["READWRITE", "READONLY", "UNAVAILABLE", "UNAVAILABLE"], "description": "Access mode (ACCESS)."}
            },
            "required": ["pool_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = f"UPDATE STGPOOL {arguments['pool_name']}"
        if arguments.get("description"): cmd += f" DESCRIPTION=\"{arguments['description']}\""
        if arguments.get("max_scratch") is not None: cmd += f" MAXSCRATCH={arguments['max_scratch']}"
        if arguments.get("reclaim") is not None: cmd += f" RECLAIM={arguments['reclaim']}"
        if arguments.get("accession"): cmd += f" ACCESS={arguments['accession']}"
        return self._execute_simple_query(cmd)

class DeleteStorageTarget(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_storage_target"
    @property
    def description(self) -> str:
        return (
            "- Description: Removes a Storage Pool. This deletes the pool definition.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- target_name (Required): Name of the storage pool to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the pool was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "target_name": {"type": "string", "description": "Storage target name."}
            },
            "required": ["target_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE STGPOOL {arguments['target_name']}")

class DeleteStoragePool(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_storage_pool"
    @property
    def description(self) -> str:
        return (
            "- Description: Deletes a **Storage Pool**. Ensure the pool is empty before deleting.\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): The name of the storage pool to delete.\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the pool was deleted."
        )
    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Pool name."}
            },
            "required": ["pool_name"]
        }
    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE STGPOOL {arguments['pool_name']}")

class QueryStorageContainer(BaseCommand):
    @property
    def name(self) -> str:
        return "query_storage_container"

    @property
    def description(self) -> str:
        return (
            "- Description: Detailed query for **Storage Pools** (Containers). Returns configuration, usage, and status.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- container_name (Optional): Specific Storage Pool name to query. If omitted, lists all.\n"
            "- format (Optional): 'standard' or 'detailed' view.\n"
            "**Output Parameters**:\n"
            "- Storage Pool Name: Unique identifier.\n"
            "- Device Class Name: underlying hardware type.\n"
            "- Estimated Capacity: Total storage available.\n"
            "- Pct Utilized: Percentage of space used.\n"
            "- Pct Migrated: Data migrated to secondary tier."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "container_name": {
                    "type": "string",
                    "description": "Name of the storage container (pool) to query. If omitted, all are displayed. (maps to pool_name)"
                },
                "format": {
                    "type": "string",
                    "enum": ["standard", "detailed"],
                    "description": "Format of the output (standard or detailed).",
                    "default": "standard"
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY STGPOOL"
        if arguments.get("container_name"):
            cmd += f" {arguments['container_name']}"
        if arguments.get("format") == "detailed":
            cmd += " FORMAT=DETAILED"
        return self._execute_simple_query(cmd)

class QueryContainerDirectory(BaseCommand):
    @property
    def name(self) -> str:
        return "query_container_directory"

    @property
    def description(self) -> str:
        return (
            "- Description: Query directories used for storage by directory-container storage pools.\n\n"
            "**Input Parameters**:\n"
            "- container_name (Optional): Storage container name.\n\n"
            "**Output Parameters**:\n"
            "- Storage Pool Name: The container using the directory.\n"
            "- Directory: The file system path.\n"
            "- Access: Current access mode (Read/Write)."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "container_name": {"type": "string", "description": "Storage container name (maps to pool name)."}
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY STGPOOLDIRECTORY"
        if arguments.get("container_name"):
            cmd += f" {arguments['container_name']}"
        return self._execute_simple_query(cmd)




class DeleteStoragePoolDirectory(BaseCommand):
    @property
    def name(self) -> str:
        return "delete_storage_pool_directory"

    @property
    def description(self) -> str:
        return (
            "Delete a directory from a directory-container storage pool.\n\n"
            "**Input Parameters**:\n"
            "- pool_name (Required): Name of the storage pool.\n"
            "- directory (Required): Directory path to remove from the pool.\n\n"
            "**Output Parameters**:\n"
            "- Result: Success message indicating the directory was deleted."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "pool_name": {"type": "string", "description": "Name of the storage pool."},
                "directory": {"type": "string", "description": "Directory path to remove from the pool."}
            },
            "required": ["pool_name", "directory"]
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        return self._execute_simple_query(f"DELETE STGPOOLDIRECTORY {arguments['pool_name']} \"{arguments['directory']}\"")


class QueryOccupancy(BaseCommand):
    @property
    def name(self) -> str:
        return "query_occupancy"

    @property
    def description(self) -> str:
        return (
            "- Description: Shows where client file spaces are stored and how much space they occupy in storage pools.\n"
            "**Input Parameters**:\n"
            "- isp_server_name (Optional): Target ISP Server name from registry.\n"
            "- node_name (Optional): Node that owns the file spaces. Wildcards supported. If omitted, all nodes are queried.\n"
            "- file_space_name (Optional): File space to locate. Wildcards supported. Requires node_name if specified.\n"
            "- stgpool (Optional): Storage pool to query. Wildcards supported. If omitted, all storage pools are queried.\n"
            "- devclass (Optional): Device class associated with storage devices. Wildcards supported.\n"
            "- type (Optional): Types of files to query (ANY, Backup, Archive, SPacem). Default: ANY.\n"
            "- nametype (Optional): How server interprets file space names (SERVER, UNIcode, FSID). Default: SERVER.\n"
            "- codetype (Optional): Code page type for file space names (BOTH, UNIcode, NONUNIcode). Default: BOTH.\n"
            "**Output Parameters**:\n"
            "- Node Name: The node that owns the file space.\n"
            "- Type: The type of data (Arch, Bkup, or SpMg).\n"
            "- Filespace Name: The name of the file space.\n"
            "- FSID: The file space ID assigned by the server.\n"
            "- Storage Pool Name: The storage pool where the file space is located.\n"
            "- Number of Files: The number of logical files stored.\n"
            "- Physical Space Occupied (MB): Physical space occupied (includes empty space within aggregates).\n"
            "- Logical Space Occupied (MB): Space occupied by logical files (excludes empty space)."
        )

    @property
    def args_schema(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "node_name": {
                    "type": "string",
                    "description": "Node that owns the file spaces. Wildcards supported."
                },
                "file_space_name": {
                    "type": "string",
                    "description": "File space to locate. Wildcards supported. Requires node_name."
                },
                "stgpool": {
                    "type": "string",
                    "description": "Storage pool to query. Wildcards supported."
                },
                "devclass": {
                    "type": "string",
                    "description": "Device class associated with storage devices. Wildcards supported."
                },
                "type": {
                    "type": "string",
                    "enum": ["ANY", "Backup", "Archive", "SPacem"],
                    "default": "ANY",
                    "description": "Types of files to query in the file spaces."
                },
                "nametype": {
                    "type": "string",
                    "enum": ["SERVER", "UNIcode", "FSID"],
                    "default": "SERVER",
                    "description": "How server interprets file space names."
                },
                "codetype": {
                    "type": "string",
                    "enum": ["BOTH", "UNIcode", "NONUNIcode"],
                    "default": "BOTH",
                    "description": "Code page type for file space names."
                }
            }
        }

    def execute(self, arguments: Dict[str, Any]) -> str:
        cmd = "QUERY OCCUPANCY"
        
        if arguments.get("node_name"):
            cmd += f" {arguments['node_name']}"
            
        if arguments.get("file_space_name"):
            cmd += f" {arguments['file_space_name']}"
            
        if arguments.get("stgpool"):
            cmd += f" STGPOOL={arguments['stgpool']}"
            
        if arguments.get("devclass"):
            cmd += f" DEVCLASS={arguments['devclass']}"
            
        if arguments.get("type"):
            cmd += f" TYPE={arguments['type']}"
            
        if arguments.get("nametype"):
            cmd += f" NAMETYPE={arguments['nametype']}"
            
        if arguments.get("codetype"):
            cmd += f" CODETYPE={arguments['codetype']}"
        
        return self._execute_simple_query(cmd)
