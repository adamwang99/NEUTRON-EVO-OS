"""
NEUTRON-EVO-OS: Shipment Rating System
Tracks USER RATINGS for each delivery.

User rating is the PRIMARY quality metric.
Combined = user_rating + time_to_ship

Rating scale:
  5 = Excellent — better than expected, no rework
  4 = Good — does what I need, minor issues
  3 = Acceptable — works but needed fixes
  2 = Poor — major issues, significant rework
  1 = Broken — not what I asked for
"""
from __future__ import annotations

import json
import filelock
from pathlib import Path
from datetime import datetime
from typing import Optional

from engine._atomic import atomic_write
import os

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
RATINGS_FILE = MEMORY_DIR / "shipments.json"
LOCK_FILE = MEMORY_DIR / "shipments.lock"


def _load() -> dict:
    """Load shipment data — called inside lock by _atomic_update only."""
    if RATINGS_FILE.exists():
        try:
            return json.loads(RATINGS_FILE.read_text())
        except Exception:
            return {"shipments": [], "counter": 0}
    return {"shipments": [], "counter": 0}


def _atomic_update(update_fn):
    """
    Thread/process-safe read-modify-write on shipments.json.
    Holds lock for the entire operation — prevents lost updates.
    """
    lock = filelock.FileLock(str(LOCK_FILE), timeout=10)
    with lock:
        data = _load()
        result = update_fn(data)
        MEMORY_DIR.mkdir(exist_ok=True)
        atomic_write(RATINGS_FILE, json.dumps(data, indent=2, ensure_ascii=False))
        return result


def _save(data: dict):
    """Save shipment data atomically (filelock + fsync + rename)."""
    lock = filelock.FileLock(str(LOCK_FILE), timeout=10)
    with lock:
        MEMORY_DIR.mkdir(exist_ok=True)
        atomic_write(RATINGS_FILE, json.dumps(data, indent=2, ensure_ascii=False))


def record_shipment(
    project: str,
    complexity: str = "MEDIUM",
    steps_completed: list = None,
    time_to_ship_minutes: float = 0,
    rating: int = None,
    rating_notes: str = "",
    outcome: str = "shipped",
    discovery_path: str = "",
    spec_path: str = "",
) -> dict:
    """
    Record a new shipment/delivery.

    Args:
        project: Project name/title
        complexity: LOW / MEDIUM / HIGH
        steps_completed: List of step names completed
        time_to_ship_minutes: Minutes from /explore to /ship
        rating: 1-5 user rating (optional, can be added later)
        rating_notes: User's notes about the rating
        outcome: shipped | abandoned_after_spec | rework_after_acceptance
        discovery_path: Path to discovery output
        spec_path: Path to SPEC.md

    Returns: {status, shipment_id, summary}
    """
    captured = [0]  # list to capture shipment_id from inner closure

    def _update(data: dict):
        new_id = data["counter"] + 1
        data["counter"] = new_id
        captured[0] = new_id
        entry = {
            "id": new_id,
            "timestamp": datetime.now().isoformat(),
            "project": project,
            "complexity": complexity,
            "steps_completed": steps_completed or [],
            "time_to_ship_minutes": time_to_ship_minutes,
            "outcome": outcome,
            "discovery_path": discovery_path,
            "spec_path": spec_path,
            "skills_used": steps_completed or [],
        }
        if rating is not None:
            entry["rating"] = rating
            entry["rating_notes"] = rating_notes
            entry["rating_timestamp"] = datetime.now().isoformat()
        data["shipments"].append(entry)
        return entry

    entry = _atomic_update(_update)

    # FEEDBACK LOOP: penalize skills that contributed to a low rating.
    # Rating 1-2 means those skills failed the user — reduce their CI.
    if rating is not None:
        _update_ci_from_rating(entry)

    return {
        "status": "recorded",
        "shipment_id": captured[0],
        "entry": entry,
        "summary": _summarize_data(_load()),
    }


def _update_ci_from_rating(shipment: dict) -> None:
    """
    Feedback loop: after rating < 3, penalize skills that contributed to failure.
    Rating 1-2 → CI drops by 3-5 per affected skill.
    This makes CI a real quality signal, not just an activity counter.
    """
    rating = shipment.get("rating")
    if rating is None:
        return

    if rating >= 4:
        # Positive: good delivery → slow upward drift
        delta = 3 if rating == 4 else 5  # rating 4 → +3, rating 5 → +5
    elif rating == 3:
        # Neutral: no change
        return
    else:
        # Negative: drop CI
        delta = -3 if rating == 2 else -5  # rating 2 → -3, rating 1 → -5

    # Map workflow step → skill name that was responsible
    step_to_skill = {
        "explore": "context",
        "discovery": "discovery",
        "spec": "spec",
        "build": "workflow",
        "verify": "workflow",
        "acceptance": "acceptance_test",
        "ship": "orchestration",
    }

    for step in shipment.get("steps_completed", []):
        skill = step_to_skill.get(step)
        if not skill:
            continue
        try:
            from engine.expert_skill_router import update_ci
            update_ci(skill, delta)
        except Exception:
            pass  # Best-effort: never block rating


def add_rating(shipment_id: int, rating: int, notes: str = "") -> dict:
    """
    Add user rating to an existing shipment.

    Rating must be 1-5.
    """
    if not (1 <= rating <= 5):
        return {"status": "error", "message": "Rating must be 1-5"}

    def _update(data: dict):
        for s in data["shipments"]:
            if s["id"] == shipment_id:
                s["rating"] = rating
                s["rating_notes"] = notes
                s["rating_timestamp"] = datetime.now().isoformat()
                return s
        return None

    updated = _atomic_update(_update)
    if updated is None:
        return {"status": "error", "message": f"Shipment {shipment_id} not found"}

    # FEEDBACK LOOP: penalize skills if this is a late post-shipment rating
    if rating is not None and rating < 3:
        _update_ci_from_rating(updated)

    return {
        "status": "updated",
        "shipment": updated,
        "summary": _summarize_data(_load()),
    }


def get_shipment(shipment_id: int) -> Optional[dict]:
    """Get a specific shipment by ID."""
    data = _load()
    for s in data["shipments"]:
        if s["id"] == shipment_id:
            return s
    return None


def get_recent(n: int = 10) -> list:
    """Get N most recent shipments."""
    data = _load()
    return sorted(data["shipments"], key=lambda s: s.get("timestamp", ""), reverse=True)[:n]


def _summarize_data(data: dict) -> dict:
    """Compute aggregate stats from shipment data."""
    shipments = data.get("shipments", [])
    if not shipments:
        return {
            "total": 0,
            "rated": 0,
            "average_rating": None,
            "average_time_to_ship_minutes": None,
            "outcome_breakdown": {},
        }

    rated = [s for s in shipments if "rating" in s]
    ratings = [s["rating"] for s in rated]
    times = [s["time_to_ship_minutes"] for s in shipments if s.get("time_to_ship_minutes")]

    outcomes = {}
    for s in shipments:
        o = s.get("outcome", "unknown")
        outcomes[o] = outcomes.get(o, 0) + 1

    return {
        "total": len(shipments),
        "rated": len(rated),
        "unrated": len(shipments) - len(rated),
        "average_rating": round(sum(ratings) / len(ratings), 1) if ratings else None,
        "average_time_to_ship_minutes": round(sum(times) / len(times), 1) if times else None,
        "outcome_breakdown": outcomes,
        "last_shipment": shipments[-1] if shipments else None,
    }


def summarize() -> dict:
    """Return full summary for UI or reporting."""
    return _summarize_data(_load())


def get_average_rating() -> float | None:
    """
    Return the rolling average user rating across all rated shipments.
    Returns None if no rated shipments exist.
    """
    data = _load()
    rated = [s["rating"] for s in data.get("shipments", []) if "rating" in s]
    if not rated:
        return None
    return round(sum(rated) / len(rated), 2)


def get_rating_for_skill(skill_name: str) -> dict:
    """
    Get aggregate rating stats for shipments involving a specific skill.
    skill_name is matched in steps_completed.
    """
    data = _load()
    skill_shipments = [
        s for s in data.get("shipments", [])
        if skill_name in s.get("skills_used", s.get("steps_completed", []))
    ]
    rated = [s["rating"] for s in skill_shipments if "rating" in s]
    if not rated:
        return {"count": len(skill_shipments), "rated": 0, "average_rating": None}
    return {
        "count": len(skill_shipments),
        "rated": len(rated),
        "average_rating": round(sum(rated) / len(rated), 2),
        "ratings": rated,
    }
