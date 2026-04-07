"""
NEUTRON-EVO-OS: Auto-Confirm Settings
Manages auto-confirm mode: skip USER REVIEW gates when enabled.

Usage:
  # Enable auto-confirm (session-wide)
  auto_confirm.enable()

  # Enable specific gates
  auto_confirm.enable(spec=True, acceptance=True)

  # Disable
  auto_confirm.disable()

  # Check current state
  auto_confirm.is_enabled()  # True/False
  auto_confirm.get_gates()   # {spec: bool, acceptance: bool}

Auto-confirm bypasses USER REVIEW gates:
  - SPEC REVIEW gate: auto-approves SPEC after AI writes it
  - ACCEPTANCE gate: auto-approves after build completes

User rating is still recorded at /ship (always, even in auto mode).
"""
from __future__ import annotations

import json
import filelock
from pathlib import Path
from datetime import datetime
from typing import Optional

from engine._atomic import atomic_write

NEUTRON_ROOT = Path(__file__).parent.parent
MEMORY_DIR = NEUTRON_ROOT / "memory"
CONFIG_FILE = MEMORY_DIR / ".auto_confirm.json"
LOCK_FILE = MEMORY_DIR / ".auto_confirm.lock"

# Defaults — gates OFF by default (user must always review)
DEFAULT = {
    "enabled": False,
    "spec": False,       # Auto-approve SPEC after AI writes it
    "discovery": False,  # Skip discovery interview, use task as-is
    "acceptance": False,  # Auto-pass acceptance after build
    "notes": "",          # Notes to add when auto-confirming
    "activated_at": None,
    "mode": "disabled",  # "full" = skip all gates, "spec_only" = skip spec only, etc.
}


def _load() -> dict:
    """Load auto-confirm config from disk."""
    if CONFIG_FILE.exists():
        try:
            return {**DEFAULT, **json.loads(CONFIG_FILE.read_text())}
        except Exception:
            pass
    return dict(DEFAULT)


def _save(cfg: dict):
    """Save auto-confirm config atomically (filelock + fsync + rename)."""
    MEMORY_DIR.mkdir(exist_ok=True)
    lock = filelock.FileLock(str(LOCK_FILE), timeout=10)
    with lock:
        atomic_write(CONFIG_FILE, json.dumps(cfg, indent=2, ensure_ascii=False))


# ─── Public API ────────────────────────────────────────────────────────────────


def is_enabled() -> bool:
    """True if any auto-confirm gate is active."""
    cfg = _load()
    return cfg.get("enabled", False)


def get_gates() -> dict:
    """Return current gate settings."""
    cfg = _load()
    return {
        "enabled": cfg.get("enabled", False),
        "spec": cfg.get("spec", False),
        "discovery": cfg.get("discovery", False),
        "acceptance": cfg.get("acceptance", False),
        "mode": cfg.get("mode", "full"),
        "notes": cfg.get("notes", ""),
    }


def enable(mode: str = "full", notes: str = "auto-confirm", _sync_platform: bool = True) -> dict:
    """
    Enable auto-confirm mode.

    Modes:
      full       — Skip all gates (discovery, SPEC, acceptance)
      spec_only  — Auto-approve SPEC only
      discovery_only — Skip discovery interview
      acceptance_only — Auto-pass acceptance only
      spec_and_acceptance — Skip SPEC + acceptance, keep discovery

    Args:
        mode: One of full, spec_only, discovery_only, acceptance_only, spec_and_acceptance
        notes: Notes to record with auto-confirmed actions
    """
    cfg = _load()
    cfg["enabled"] = True
    cfg["mode"] = mode
    cfg["notes"] = notes
    cfg["activated_at"] = datetime.now().isoformat()

    if mode == "full":
        cfg["spec"] = True
        cfg["discovery"] = True
        cfg["acceptance"] = True
    elif mode == "spec_only":
        cfg["spec"] = True
        cfg["discovery"] = False
        cfg["acceptance"] = False
    elif mode == "discovery_only":
        cfg["discovery"] = True
        cfg["spec"] = False
        cfg["acceptance"] = False
    elif mode == "acceptance_only":
        cfg["acceptance"] = True
        cfg["spec"] = False
        cfg["discovery"] = False
    elif mode == "spec_and_acceptance":
        cfg["spec"] = True
        cfg["acceptance"] = True
        cfg["discovery"] = False
    else:
        return {"status": "error", "message": f"Unknown mode: {mode}"}

    _save(cfg)

    # ── Platform Sync ──────────────────────────────────────────────────────────
    # When auto-confirm is enabled, sync settings to ALL AI IDE platforms
    # so the user never sees permission prompts.
    _sync_output = ""
    if _sync_platform:
        try:
            from engine.platform_sync import sync_all, format_sync_results
            sync_results = sync_all(enabled=True)
            _sync_output = format_sync_results(sync_results)
        except Exception as e:
            _sync_output = f"\n⚠️  Platform sync skipped: {e}"

    return {
        "status": "enabled",
        "mode": mode,
        "notes": notes,
        "gates": {"spec": cfg["spec"], "discovery": cfg["discovery"], "acceptance": cfg["acceptance"]},
        "message": _format_message(mode) + _sync_output,
    }


def disable() -> dict:
    """Disable auto-confirm. All gates require user action."""
    cfg = _load()
    cfg["enabled"] = False
    cfg["spec"] = False
    cfg["discovery"] = False
    cfg["acceptance"] = False
    cfg["mode"] = "disabled"
    _save(cfg)

    # ── Platform Sync: restore safe defaults ──────────────────────────────────
    _sync_output = ""
    try:
        from engine.platform_sync import sync_all, format_sync_results
        sync_results = sync_all(enabled=False)
        _sync_output = format_sync_results(sync_results)
    except Exception as e:
        _sync_output = f"\n⚠️  Platform restore skipped: {e}"

    return {
        "status": "disabled",
        "message": "Auto-confirm OFF. All gates require user action." + _sync_output,
    }


def toggle() -> dict:
    """Toggle auto-confirm on/off."""
    if is_enabled():
        return disable()
    else:
        return enable("full")


def should_skip(step: str) -> bool:
    """
    Should this workflow step be auto-confirmed?

    Args:
        step: One of "discovery", "spec", "acceptance"

    Returns:
        True if auto-confirm is enabled for this gate, False otherwise.
    """
    cfg = _load()
    if not cfg.get("enabled"):
        return False
    return cfg.get(step, False)


def record_auto_action(step: str, context: dict) -> dict:
    """
    Record an auto-confirmed action in the audit trail.
    Returns the auto-confirmed result dict for this step.
    """
    cfg = _load()
    notes = cfg.get("notes", "auto-confirm")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    # Log the auto-confirm
    _log_auto_action(step, notes)

    return {
        "status": f"{step}_auto_confirmed",
        "output": f"[AUTO-CONFIRM] {step.capitalize()} approved automatically (mode={cfg.get('mode', '?')})",
        "ci_delta": 0,
        "auto_confirmed": True,
        "notes": notes,
        "timestamp": now,
    }


def _log_auto_action(step: str, notes: str):
    """Append auto-confirm action to today's memory log (filelock to prevent truncation)."""
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = MEMORY_DIR / f"{today}.md"
    ts = datetime.now().strftime("%H:%M")
    entry = (
        f"\n## [{ts}] — AUTO-CONFIRM: /{step}\n"
        f"- Action: {step} auto-approved\n"
        f"- Mode: auto-confirm enabled\n"
        f"- Notes: {notes}\n"
    )
    try:
        lock_path = log_path.with_suffix(".lock")
        with filelock.FileLock(str(lock_path), timeout=10):
            content = log_path.read_text(errors="replace") if log_path.exists() else f"# {today}\n"
            atomic_write(log_path, content + entry + "\n")
    except Exception as e:
        import sys
        print(f"[AUTO-CONFIRM] WARNING: Failed to log auto-action to {log_path}: {e}", file=sys.stderr)


def _format_message(mode: str) -> str:
    """Human-readable description of auto-confirm mode."""
    messages = {
        "full": (
            "🔓 AUTO-CONFIRM FULL MODE — All gates skipped:\n"
            "  • Discovery interview: SKIPPED\n"
            "  • SPEC review: AUTO-APPROVED\n"
            "  • Acceptance test: AUTO-PASSED\n\n"
            "⚠️  WARNING: User rating at /ship is still recorded.\n"
            "   Use /auto disable if you want full human control."
        ),
        "spec_only": (
            "🔓 AUTO-CONFIRM SPEC ONLY — SPEC review skipped:\n"
            "  • Discovery interview: REQUIRED\n"
            "  • SPEC review: AUTO-APPROVED\n"
            "  • Acceptance test: REQUIRED\n"
        ),
        "discovery_only": (
            "🔓 AUTO-CONFIRM DISCOVERY ONLY:\n"
            "  • Discovery interview: SKIPPED\n"
            "  • SPEC review: REQUIRED\n"
            "  • Acceptance test: REQUIRED\n"
        ),
        "acceptance_only": (
            "🔓 AUTO-CONFIRM ACCEPTANCE ONLY:\n"
            "  • Discovery interview: REQUIRED\n"
            "  • SPEC review: REQUIRED\n"
            "  • Acceptance test: AUTO-PASSED\n"
        ),
        "spec_and_acceptance": (
            "🔓 AUTO-CONFIRM SPEC + ACCEPTANCE:\n"
            "  • Discovery interview: REQUIRED\n"
            "  • SPEC review: AUTO-APPROVED\n"
            "  • Acceptance test: AUTO-PASSED\n"
        ),
    }
    return messages.get(mode, messages["full"])
