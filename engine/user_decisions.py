"""
NEUTRON-EVO-OS: User Decisions Log
Tracks only USER DECISIONS — not skill executions.

Memory principle: preserve what the USER chose, not what the AI did.
Skill executions are noise. User decisions are signal.
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
DECISIONS_FILE = MEMORY_DIR / "user_decisions.json"
LOCK_FILE = MEMORY_DIR / "user_decisions.lock"


def _load() -> list:
    """Load all decisions from disk."""
    if DECISIONS_FILE.exists():
        try:
            return json.loads(DECISIONS_FILE.read_text())
        except Exception:
            return []
    return []


def _save(decisions: list):
    """Save decisions to disk atomically (filelock + fsync + rename)."""
    MEMORY_DIR.mkdir(exist_ok=True)
    lock = filelock.FileLock(str(LOCK_FILE), timeout=10)
    with lock:
        atomic_write(DECISIONS_FILE, json.dumps(decisions, indent=2, ensure_ascii=False))


def record(
    decision: str,
    context: str = "",
    project: str = "",
    outcome: str = "pending",
) -> dict:
    """
    Record a user decision.

    Args:
        decision: What the user decided (e.g., "SPEC approved", "Use PostgreSQL")
        context: Why they decided it, or what options were considered
        project: Which project this relates to
        outcome: pending | accepted | rejected

    Returns: {status, decision_id, entry}
    """
    lock = filelock.FileLock(str(DECISIONS_FILE.with_suffix(".lock")), timeout=10)
    try:
        lock.acquire(timeout=10)
    except filelock.Timeout:
        return {"status": "error", "output": "Lock timeout — try again", "ci_delta": -1}
    try:
        decisions = _load()
        # Assign ID inside the lock: len() is safe since we hold the lock
        new_id = max((d.get("id", 0) for d in decisions), default=0) + 1
        entry = {
            "id": new_id,
            "timestamp": datetime.now().isoformat(),
            "decision": decision,
            "context": context,
            "project": project,
            "outcome": outcome,
        }
        decisions.append(entry)
        atomic_write(DECISIONS_FILE, json.dumps(decisions, indent=2, ensure_ascii=False))
        return {"status": "recorded", "decision_id": entry["id"], "entry": entry}
    finally:
        lock.release()


def get_recent(n: int = 10, project: str = "") -> list:
    """Get N most recent decisions, optionally filtered by project."""
    decisions = _load()
    if project:
        decisions = [d for d in decisions if d.get("project", "") == project]
    return sorted(decisions, key=lambda d: d.get("timestamp", ""), reverse=True)[:n]


def get_project_decisions(project: str) -> list:
    """Get all decisions for a specific project."""
    return [d for d in _load() if d.get("project", "") == project]


def update_outcome(decision_id: int, outcome: str, notes: str = "") -> dict:
    """
    Update the outcome of a decision.
    outcome: pending | accepted | rejected | modified
    """
    lock = filelock.FileLock(str(DECISIONS_FILE.with_suffix(".lock")), timeout=10)
    try:
        lock.acquire(timeout=10)
    except filelock.Timeout:
        return {"status": "error", "output": "Lock timeout — try again", "ci_delta": -1}
    try:
        decisions = _load()
        for d in decisions:
            if d.get("id") == decision_id:
                d["outcome"] = outcome
                d["outcome_updated_at"] = datetime.now().isoformat()
                if notes:
                    d["outcome_notes"] = notes
                atomic_write(DECISIONS_FILE, json.dumps(decisions, indent=2, ensure_ascii=False))
                return {"status": "updated", "entry": d}
        return {"status": "error", "message": f"Decision {decision_id} not found"}
    finally:
        lock.release()


def summarize() -> dict:
    """Return a summary of all decisions for the system."""
    decisions = _load()
    if not decisions:
        return {
            "total": 0,
            "by_outcome": {},
            "by_project": {},
            "last_decision": None,
        }
    by_outcome = {}
    by_project = {}
    for d in decisions:
        o = d.get("outcome", "pending")
        by_outcome[o] = by_outcome.get(o, 0) + 1
        p = d.get("project", "unknown")
        by_project[p] = by_project.get(p, 0) + 1
    return {
        "total": len(decisions),
        "by_outcome": by_outcome,
        "by_project": by_project,
        "last_decision": decisions[-1] if decisions else None,
    }
