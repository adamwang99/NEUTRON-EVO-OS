"""
NEUTRON EVO OS — Context Snapshot
Saves conversation state to disk for session recovery after context compaction or loss.

Snapshots are written atomically and are read by the SessionStart hook to show
"What was in progress" to the next session.

File: memory/.context_snapshot.json
"""
from __future__ import annotations

import json
import os
import filelock
from pathlib import Path
from datetime import datetime
from typing import Optional

from engine._atomic import atomic_write

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
SNAPSHOT_FILE = MEMORY_DIR / ".context_snapshot.json"
SNAPSHOT_LOCK = MEMORY_DIR / ".context_snapshot.lock"

# Max age before snapshot is considered stale (session was likely abandoned)
STALE_THRESHOLD_HOURS = 4


def _load_snapshot() -> dict:
    """Load existing snapshot if present and not stale."""
    if not SNAPSHOT_FILE.exists():
        return {}
    try:
        data = json.loads(SNAPSHOT_FILE.read_text())
        # Check staleness
        ts = data.get("snapshot_at", "")
        if ts:
            try:
                snap_dt = datetime.fromisoformat(ts)
                age = (datetime.now() - snap_dt).total_seconds() / 3600
                if age > STALE_THRESHOLD_HOURS:
                    return {}  # stale — treat as empty
            except Exception:
                return {}
        return data
    except Exception:
        return {}


def save_snapshot(
    task: str = "",
    pending_fixes: list[str] = None,
    modified_files: list[str] = None,
    decisions: list[str] = None,
    current_step: str = "",
    notes: str = "",
    test_status: str = "unknown",
) -> dict:
    """
    Save a context snapshot atomically (filelock + fsync + rename).

    Call this:
      - After completing each fix (modified_files, task, test_status)
      - Before starting a new session work block
      - In pre-tool hooks to preserve context across compaction

    Args:
        task: What task is in progress
        pending_fixes: List of fixes that were attempted but not completed
        modified_files: List of files modified in this session
        decisions: Key decisions made (e.g., "chose atomic_write over filelock+write")
        current_step: Current workflow step or milestone
        notes: Free-form notes
        test_status: "passed" | "failed" | "unknown"
    """
    pending_fixes = pending_fixes or []
    modified_files = modified_files or []
    decisions = decisions or []

    data = {
        "snapshot_at": datetime.now().isoformat(),
        "task": task,
        "pending_fixes": pending_fixes,
        "modified_files": modified_files,
        "decisions": decisions,
        "current_step": current_step,
        "notes": notes,
        "test_status": test_status,
    }

    lock = filelock.FileLock(str(SNAPSHOT_LOCK), timeout=10)
    with lock:
        atomic_write(SNAPSHOT_FILE, json.dumps(data, indent=2, ensure_ascii=False))

    return {"status": "saved", "snapshot_at": data["snapshot_at"]}


def load_snapshot() -> dict:
    """Load current snapshot for recovery or display."""
    lock = filelock.FileLock(str(SNAPSHOT_LOCK), timeout=10)
    with lock:
        data = _load_snapshot()
    return data


def clear_snapshot() -> dict:
    """Clear the snapshot (e.g., after successful completion)."""
    lock = filelock.FileLock(str(SNAPSHOT_LOCK), timeout=10)
    with lock:
        if SNAPSHOT_FILE.exists():
            SNAPSHOT_FILE.unlink()
    return {"status": "cleared"}


def get_snapshot_summary() -> str:
    """
    Return a human-readable summary of the current snapshot.
    Used by SessionStart hook to display "what to pick up".
    """
    data = load_snapshot()
    if not data:
        return ""

    lines = []
    if data.get("task"):
        lines.append(f"  📋 Task: {data['task']}")
    if data.get("current_step"):
        lines.append(f"  📍 Step: {data['current_step']}")
    if data.get("modified_files"):
        files = data["modified_files"][:8]  # show first 8
        lines.append(f"  📁 Modified: {', '.join(files)}")
    if data.get("pending_fixes"):
        lines.append(f"  ⚠️  Pending: {', '.join(data['pending_fixes'][:5])}")
    if data.get("decisions"):
        lines.append(f"  💡 Decisions: {data['decisions'][-1] if data['decisions'] else ''}")
    if data.get("test_status"):
        icon = "✅" if data["test_status"] == "passed" else "❌" if data["test_status"] == "failed" else "⏳"
        lines.append(f"  {icon} Tests: {data['test_status']}")

    return "\n".join(lines)
