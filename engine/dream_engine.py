"""
NEUTRON-EVO-OS: Dream Engine — Memory 2.0 Core
Implements Pruning (delete noise) and Distillation (compress logs into Cookbooks).
"""
from __future__ import annotations

import json
import os
import shutil
import threading
from pathlib import Path
from datetime import datetime, timedelta

from engine.smart_observer import SilentObserver

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
ARCHIVED_DIR = MEMORY_DIR / "archived"
COOKBOOKS_DIR = MEMORY_DIR / "cookbooks"
NOISE_THRESHOLD_DAYS = 3   # days old before archiving
ARCHIVED_RETENTION_DAYS = 7  # max age for archived files

# Re-entrancy guard: prevents concurrent dream cycles
_dream_running = threading.Event()

# Sentinel file — if this file exists, observer should NOT restart dream cycle
# Prevents re-trigger after the cycle itself creates files
_DREAM_SENTINEL = MEMORY_DIR / ".dream_active"


def dream_cycle(json_output: bool = True) -> dict | str:
    """
    Execute a full Dream Cycle:
    1. Archive today's logs to /memory/archived/
    2. Prune noise (files not referenced in N days)
    3. Distill remaining logs into Cookbooks
    4. Cap archived/ retention (max age or max count)

    Args:
        json_output: if True (default), returns a JSON string (for CLI/print output).
                     if False, returns a dict (for programmatic use).

    Returns: dict, or JSON string if json_output=True.

    Note: Does NOT restart the observer — observer lifecycle is managed externally
    by make live or engine skill observer_start/observer_stop.
    """
    if _dream_running.is_set():
        result = {"status": "skipped", "reason": "already running"}
        return json.dumps(result) if json_output else result

    _dream_running.set()
    try:
        # Write sentinel BEFORE doing work — prevents observer from re-triggering
        _DREAM_SENTINEL.write_text(datetime.now().isoformat())
        result = _dream_cycle_inner()
        return json.dumps(result) if json_output else result
    finally:
        _dream_running.clear()
        # Remove sentinel AFTER work is done — observer can now safely trigger
        try:
            _DREAM_SENTINEL.unlink(missing_ok=True)
        except Exception:
            pass


def _dream_cycle_inner() -> dict:
    """Inner dream cycle logic (called within re-entrancy guard)."""
    # Ensure dirs exist
    ARCHIVED_DIR.mkdir(exist_ok=True)
    COOKBOOKS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    now = datetime.now()

    # --- Archive Phase ---
    # Only archive files at top level of memory/ — never subdirectories.
    # Filter out subdirectory entries explicitly.
    archived_count = 0
    archived_files = []
    for log in MEMORY_DIR.iterdir():
        if not (log.is_file() and log.suffix == ".md"):
            continue
        # Skip sentinel file
        if log.name.startswith(".dream_active"):
            continue
        dest = ARCHIVED_DIR / f"{log.stem}_{timestamp}{log.suffix}"
        shutil.copy2(log, dest)
        archived_files.append(log.name)
        archived_count += 1

    # --- Prune Phase (old .tmp/.cache files only) ---
    cutoff = now - timedelta(days=NOISE_THRESHOLD_DAYS)
    pruned_files = []
    for item in list(MEMORY_DIR.iterdir()) + list(ARCHIVED_DIR.iterdir()):
        if item.name in ("archived", "cookbooks", ".dream_active"):
            continue
        if item.is_file() and item.suffix in (".tmp", ".cache"):
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime < cutoff:
                item.unlink()
                pruned_files.append(item.name)

    # --- Archive Retention Cap ---
    # Cap archived/ to ARCHIVED_RETENTION_DAYS (default 7 days).
    # Sort by mtime, delete oldest beyond threshold.
    archived_cutoff = now - timedelta(days=ARCHIVED_RETENTION_DAYS)
    deleted_retention = 0
    for archived_file in sorted(ARCHIVED_DIR.iterdir(), key=lambda f: f.stat().st_mtime):
        mtime = datetime.fromtimestamp(archived_file.stat().st_mtime)
        if mtime < archived_cutoff:
            archived_file.unlink()
            deleted_retention += 1

    # --- Distill Phase (top-level .md only) ---
    distilled = []
    for log in MEMORY_DIR.iterdir():
        if not (log.is_file() and log.suffix == ".md"):
            continue
        if log.name.startswith(".dream_active"):
            continue
        result = distill_log(str(log))
        if result.get("status") == "distilled":
            distilled.append(result["cookbook"])

    # --- Stop observer during dream cycle (avoid re-trigger) ---
    try:
        SilentObserver.stop()
    except Exception:
        pass

    return {
        "status": "dream_complete",
        "timestamp": timestamp,
        "archived": archived_count,
        "archived_files": archived_files,
        "pruned": len(pruned_files),
        "pruned_files": pruned_files,
        "distilled": len(distilled),
        "cookbooks": distilled,
        "retention_deleted": deleted_retention,
    }


def distill_log(log_path: str) -> dict:
    """
    Compress a log into a Cookbook summary.
    Extracts key patterns and stores compressed version.

    Returns: {status, cookbook, entries_extracted}
    """
    path = Path(log_path)
    if not path.exists():
        return {"status": "error", "message": f"Log not found: {log_path}"}

    content = path.read_text()
    lines = [l.strip() for l in content.splitlines() if l.strip()]

    # Extract key event lines (lines with timestamps, action markers, decisions)
    key_lines = [
        l for l in lines
        if any(kw in l.lower() for kw in ["action:", "outcome:", "decision:", "ci delta", "##"])
    ]

    if not key_lines:
        return {"status": "skipped", "message": "No distillable content found"}

    # Build cookbook
    cookbook_name = f"{path.stem}_cookbook.md"
    cookbook_path = COOKBOOKS_DIR / cookbook_name

    cookbook_content = [
        f"# Cookbook: {path.stem}",
        "",
        f"> Distilled from {path.name} on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> ∫f(t)dt — Functional Credibility Over Institutional Inertia",
        "",
        f"## Key Events ({len(key_lines)} entries)",
        "",
    ]
    for line in key_lines[:100]:  # cap at 100 lines
        cookbook_content.append(line)

    cookbook_path.write_text("\n".join(cookbook_content))

    return {
        "status": "distilled",
        "cookbook": str(cookbook_path),
        "entries_extracted": len(key_lines),
    }


def archive_user_data(file_path: str) -> dict:
    """
    Safely archive user data to /memory/archived/.
    Returns: {status, archived_to}
    """
    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "message": f"File not found: {file_path}"}

    ARCHIVED_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived_name = f"{path.stem}_{timestamp}{path.suffix}"
    archived_path = ARCHIVED_DIR / archived_name

    shutil.copy2(path, archived_path)

    return {
        "status": "archived",
        "archived_to": str(archived_path),
        "original": str(path),
    }
