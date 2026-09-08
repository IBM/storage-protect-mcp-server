import os
import stat
import logging
from dataclasses import dataclass, field
from typing import Optional, Dict

try:
    import keyring as _keyring
    _KEYRING_AVAILABLE = True
except ImportError:
    _keyring = None
    _KEYRING_AVAILABLE = False

logger = logging.getLogger(__name__)

_KEYRING_SERVICE = "ibm-sp-mcp-server"

# Ordered from narrowest to broadest privilege.
# credential_for() selects the narrowest credential that satisfies the
# required_privilege of the loaded tool set.
PRIVILEGE_TIERS = ("any", "operator", "storage", "policy", "system")


@dataclass
class ModuleCredential:
    """Credential pair for one SP privilege tier."""
    admin_id: str
    admin_password: str
    privilege: str  # 'system' | 'policy' | 'storage' | 'operator' | 'any'


@dataclass
class ServerConfig:
    # Connection
    server_address: Optional[str]
    server_port: str

    # Per-module credentials (keyed by privilege tier).
    # Populated from SP_ADMIN_ID_SYSTEM / SP_ADMIN_PASSWORD_SYSTEM, etc.
    credentials: Dict[str, ModuleCredential] = field(default_factory=dict)

    # Legacy single-credential fallback (used when per-module vars not set).
    # Deprecated — migrate to per-module vars for least-privilege operation.
    admin_id: Optional[str] = None
    admin_password: Optional[str] = None

    # Optional paths
    dsmserv_path: Optional[str] = None
    server_instance_dir: Optional[str] = None
    servermon_path: Optional[str] = None
    servermon_xml_dir: Optional[str] = None
    instance_user: Optional[str] = None

    def credential_for(self, privilege: str) -> Optional[ModuleCredential]:
        """
        Return the narrowest available credential that satisfies *privilege*.

        Walk from the requested tier down to 'any', return the first match.
        Falls back to the legacy single credential if no per-module creds are set.
        """
        if privilege not in PRIVILEGE_TIERS:
            raise ValueError(
                f"Unknown privilege tier '{privilege}'. "
                f"Valid values: {PRIVILEGE_TIERS}"
            )
        # Walk from requested tier down to narrowest — prefer exact or closest match
        search_order = PRIVILEGE_TIERS[: PRIVILEGE_TIERS.index(privilege) + 1]
        for tier in reversed(search_order):
            if tier in self.credentials:
                return self.credentials[tier]

        # Legacy fallback
        if self.admin_id and self.admin_password:
            return ModuleCredential(
                admin_id=self.admin_id,
                admin_password=self.admin_password,
                privilege="system",   # assume worst-case for legacy config
            )
        return None

    def validate(self) -> bool:
        """Return True when at least one credential is configured."""
        return bool(self.credentials) or bool(self.admin_id and self.admin_password)


# ── CRED-3: .env permission guard ─────────────────────────────────────────────

def _load_env_permission_check(env_path: str = ".env") -> None:
    """
    CRED-3: Fail fast if the .env file is readable by group or other.
    Must be called *before* dotenv loads the file so secrets are never
    materialised when the file permissions are insecure.
    """
    if not os.path.exists(env_path):
        return
    mode = os.stat(env_path).st_mode
    if mode & (stat.S_IRGRP | stat.S_IROTH | stat.S_IWGRP | stat.S_IWOTH):
        raise PermissionError(
            f"SECURITY [CRED-3]: '{env_path}' has insecure permissions "
            f"({oct(mode & 0o777)}). Restrict to owner-only: chmod 600 {env_path}"
        )


def check_env_file_permissions(env_path: str = ".env") -> None:
    """
    Public helper imported by each entry-point (main.py, etc.).
    Prints the error and calls sys.exit(1) so callers don't need to handle it.
    """
    try:
        _load_env_permission_check(env_path)
    except PermissionError as exc:
        import sys
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)


def secure_startup(env_path: str = ".env") -> None:
    """
    CRED-3 / RG-2: Atomic helper that enforces .env permission check before
    loading dotenv.  Import and call this from every main_*.py entry point
    instead of calling check_env_file_permissions() and load_dotenv() separately.
    This prevents accidental omission of the permission guard in new entry points.
    """
    check_env_file_permissions(env_path)
    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
    except ImportError:
        pass  # python-dotenv not installed; env vars already set by process environment


# ── Configuration loader ───────────────────────────────────────────────────────

def _get_password(admin_id: Optional[str], env_var: str) -> Optional[str]:
    """
    INT-4: Retrieve a service account password.
    Resolution order:
      1. OS keyring (keyed by admin_id under service 'ibm-sp-mcp-server')
      2. Environment variable named env_var
    Returns None when neither source has the password.
    """
    if admin_id and _KEYRING_AVAILABLE and _keyring is not None:
        try:
            kr_value = _keyring.get_password(_KEYRING_SERVICE, admin_id)
            if kr_value:
                logger.debug(
                    "INT-4: Password for '%s' retrieved from OS keyring.", admin_id
                )
                return kr_value
        except Exception as kr_exc:
            logger.debug(
                "INT-4: Keyring lookup failed for '%s': %s. Falling back to env var.",
                admin_id, kr_exc,
            )

    env_value = os.environ.get(env_var)
    if env_value and admin_id:
        logger.debug(
            "INT-4: Password for '%s' retrieved from environment variable %s. "
            "Consider migrating to keyring for better security.",
            admin_id, env_var,
        )
    return env_value


def load_config(env_path: str = ".env") -> ServerConfig:
    """Load configuration from keyring (primary) or environment variables (fallback).

    CRED-3: The .env permission check runs first so the process aborts
    before any secret is read from an insecure file.
    INT-4: Passwords are resolved from the OS keyring before falling back to env vars.
    """
    _load_env_permission_check(env_path)

    address = os.environ.get("TCPSERVERADDRESS")
    port    = os.environ.get("SP_SERVER_PORT") or os.environ.get("TCPPORT") or "1500"

    # ── CRED-1 + INT-4: Per-module credentials (keyring-first) ───────────────
    credentials: Dict[str, ModuleCredential] = {}

    _module_map = {
        "system":   ("SP_ADMIN_ID_SYSTEM",   "SP_ADMIN_PASSWORD_SYSTEM"),
        "policy":   ("SP_ADMIN_ID_POLICY",   "SP_ADMIN_PASSWORD_POLICY"),
        "storage":  ("SP_ADMIN_ID_STORAGE",  "SP_ADMIN_PASSWORD_STORAGE"),
        "operator": ("SP_ADMIN_ID_OPERATOR", "SP_ADMIN_PASSWORD_OPERATOR"),
        "any":      ("SP_ADMIN_ID_READONLY", "SP_ADMIN_PASSWORD_READONLY"),
    }
    for privilege, (id_var, pw_var) in _module_map.items():
        admin_id = os.environ.get(id_var)
        if not admin_id:
            continue
        # INT-4: keyring-first password resolution
        admin_pwd = _get_password(admin_id, pw_var)
        if admin_pwd:
            credentials[privilege] = ModuleCredential(
                admin_id=admin_id,
                admin_password=admin_pwd,
                privilege=privilege,
            )

    # ── Legacy single-credential fallback ─────────────────────────────────────
    legacy_id  = os.environ.get("SP_ADMIN_ID")
    legacy_pwd = _get_password(legacy_id, "SP_ADMIN_PASSWORD") if legacy_id else None

    if legacy_id and legacy_pwd and not credentials:
        logger.warning(
            "CRED-1 / INT-4: Using legacy single-credential SP_ADMIN_ID/SP_ADMIN_PASSWORD. "
            "Migrate to per-module credentials (SP_ADMIN_ID_SYSTEM, etc.) with keyring storage "
            "for least-privilege, credential-manager-backed operation."
        )

    return ServerConfig(
        server_address=address,
        server_port=port,
        credentials=credentials,
        admin_id=legacy_id,
        admin_password=legacy_pwd,
        dsmserv_path=os.environ.get("SP_DSMSERV_PATH"),
        server_instance_dir=os.environ.get("SP_SERVER_INSTANCE_DIR"),
        servermon_path=os.environ.get("SP_SERVERMON_PATH"),
        servermon_xml_dir=os.environ.get("SP_SERVERMON_XML_DIR"),
        instance_user=os.environ.get("SP_INSTANCE_USER"),
    )
