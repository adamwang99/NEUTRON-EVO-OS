"""
NEUTRON EVO OS — MCP Server Configuration
Manages API keys, NEUTRON_ROOT per key, and server settings.
Loads from memory/.mcp_config.json (auto-created on first run).
"""
from __future__ import annotations

import json
import secrets
import os
from pathlib import Path
from datetime import datetime

_NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", str(Path(__file__).parent.parent)))
_CONFIG_FILE = _NEUTRON_ROOT / "memory" / ".mcp_config.json"


def _load() -> dict:
    """Load MCP config from disk. Creates default if missing/corrupted."""
    if _CONFIG_FILE.exists():
        try:
            return json.loads(_CONFIG_FILE.read_text())
        except Exception:
            # Corrupted — backup before overwriting
            import shutil, datetime
            backup_dir = _CONFIG_FILE.parent / ".config_backup"
            backup_dir.mkdir(exist_ok=True)
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            shutil.copy2(_CONFIG_FILE, backup_dir / f"mcp_config.corrupted.{ts}.json")
    # First run or recovery — create and persist default config
    cfg = _default_config()
    _save(cfg)
    return cfg


def _save(cfg: dict):
    """Save MCP config atomically."""
    _CONFIG_FILE.parent.mkdir(exist_ok=True)
    _CONFIG_FILE.write_text(json.dumps(cfg, indent=2, ensure_ascii=False))


def _default_config() -> dict:
    """Default config: single key → current NEUTRON_ROOT."""
    default_key = secrets.token_urlsafe(32)
    return {
        "version": "1.0",
        "created_at": datetime.now().isoformat(),
        "default_neutron_root": str(_NEUTRON_ROOT),
        "keys": {
            default_key: {
                "label": "default",
                "neutron_root": str(_NEUTRON_ROOT),
                "created_at": datetime.now().isoformat(),
                "rate_limit": 60,  # req/min
                "enabled": True,
            }
        },
        "server": {
            "port": 3100,
            "host": "127.0.0.1",
            "cors_origins": ["*"],
            "request_timeout": 30,
        },
    }


def get_neutron_root(api_key: str | None = None) -> str | None:
    """
    Resolve NEUTRON_ROOT for an API key.
    If api_key is None, returns default_neutron_root.
    """
    cfg = _load()
    if api_key is None:
        return cfg.get("default_neutron_root", str(_NEUTRON_ROOT))
    key_entry = cfg.get("keys", {}).get(api_key)
    if not key_entry:
        return None
    if not key_entry.get("enabled", True):
        return None
    return key_entry.get("neutron_root")


def validate_api_key(api_key: str) -> tuple[bool, str | None]:
    """
    Validate an API key.
    Returns (is_valid, neutron_root_or_error).
    """
    cfg = _load()
    key_entry = cfg.get("keys", {}).get(api_key)

    if not key_entry:
        return False, "Invalid API key"

    if not key_entry.get("enabled", True):
        return False, "API key disabled"

    root = key_entry.get("neutron_root")
    if root and not Path(root).exists():
        return False, f"NEUTRON_ROOT not found: {root}"

    return True, root


def get_server_config() -> dict:
    """Return server settings (port, host, cors, timeout)."""
    cfg = _load()
    return cfg.get("server", {
        "port": 3100,
        "host": "127.0.0.1",
        "cors_origins": ["*"],
        "request_timeout": 30,
    })


def create_api_key(label: str, neutron_root: str | None = None, rate_limit: int = 60) -> str:
    """Generate a new API key with a label and neutron_root."""
    cfg = _load()
    key = secrets.token_urlsafe(32)
    cfg["keys"][key] = {
        "label": label,
        "neutron_root": neutron_root or cfg.get("default_neutron_root", str(_NEUTRON_ROOT)),
        "created_at": datetime.now().isoformat(),
        "rate_limit": rate_limit,
        "enabled": True,
    }
    _save(cfg)
    return key


def revoke_api_key(api_key: str) -> bool:
    """Revoke (disable) an API key."""
    cfg = _load()
    if api_key in cfg.get("keys", {}):
        cfg["keys"][api_key]["enabled"] = False
        _save(cfg)
        return True
    return False


def list_keys() -> list[dict]:
    """List all API keys (hiding the actual key values)."""
    cfg = _load()
    return [
        {
            "key_hint": key[-4:],
            "label": v["label"],
            "neutron_root": v["neutron_root"],
            "rate_limit": v.get("rate_limit", 60),
            "enabled": v.get("enabled", True),
            "created_at": v.get("created_at", ""),
        }
        for key, v in cfg.get("keys", {}).items()
    ]


def get_rate_limit(api_key: str) -> int:
    """Get rate limit (req/min) for an API key."""
    cfg = _load()
    return cfg.get("keys", {}).get(api_key, {}).get("rate_limit", 60)
