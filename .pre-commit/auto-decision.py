#!/usr/bin/env python3
"""
auto-decision.py — pre-commit hook
Automatically records TECH CHOICES as user decisions when files change.
No user action needed — decision is inferred from commit message and files changed.

Triggers:
  - feat:     → "Chose [file/area] for [description]"
  - fix:      → "Fixed [area]: [description]"
  - refactor: → "Refactored [area]: [description]"
  - docs:     → "Documented [area]: [description]"
  - chore:    → "Maintained [area]: [description]"
  - test:     → "Added tests for [area]: [description]"

Skip conditions:
  - SKIP if already recorded in last 5 minutes (debounce)
  - SKIP if NEUTRON_DREAM_TEST=1 (test mode)
"""
from __future__ import annotations

import os
import re
import sys
import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
DECISIONS_FILE = MEMORY_DIR / "user_decisions.json"
DEBOUNCE_FILE = MEMORY_DIR / ".decision_debounce.json"


def get_commit_msg() -> str:
    """Get commit message from pre-commit stdin/file."""
    for arg in sys.argv[1:]:
        if arg.endswith(".msg") or "COMMIT_EDITMSG" in arg:
            try:
                return Path(arg).read_text()
            except Exception:
                pass
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def get_changed_files() -> list[str]:
    """Get list of files staged for commit."""
    files = []
    for arg in sys.argv[1:]:
        p = Path(arg)
        if p.exists() and not p.is_dir():
            files.append(str(p))
    return files


def summarize_area(files: list[str]) -> str:
    """Infer the area/component from changed files."""
    area_counts = {}
    for f in files:
        # Strip file extension to avoid "active-recall.py" → "active-recall"
        f_clean = re.sub(r"\.(py|sh|js|ts|tsx|md|yaml|json|toml)$", "", f)
        parts = f_clean.replace("\\", "/").split("/")
        # Known areas — check from most specific to least specific
        for prefix, area_name in [
            ("skills/core/", "skills"),
            ("skills/", "skills"),
            ("engine/", "engine"),
            ("mcp_server/", "mcp_server"),
            ("hooks/", "hooks"),
            (".pre-commit/", "pre-commit"),
            ("docs/", "docs"),
            ("memory/", "memory"),
        ]:
            if prefix in f:
                area = area_name
                area_counts[area] = area_counts.get(area, 0) + 1
                break
        else:
            if any(parts[-1].endswith(ext) for ext in [".py", ".sh", ".js", ".ts"]):
                area_counts["core"] = area_counts.get("core", 0) + 1
            else:
                area_counts["general"] = area_counts.get("general", 0) + 1

    if not area_counts:
        return "general"
    return max(area_counts, key=area_counts.get)


def parse_commit(msg: str) -> tuple[str | None, str | None, str | None]:
    """
    Parse commit message.
    Returns: (type, description, area) or (None, None, None).
    """
    msg = msg.strip()
    m = re.match(r"^(\w+):\s*(.+)", msg)
    if not m:
        return None, None, None

    ctype = m.group(1).lower()
    body = m.group(2).strip()

    # Shorten description
    if len(body) > 80:
        body = body[:77] + "..."

    type_map = {
        "feat": "New feature",
        "fix": "Bug fix",
        "refactor": "Refactoring",
        "docs": "Documentation",
        "chore": "Maintenance",
        "test": "Test",
        "perf": "Performance",
        "style": "Style",
        "ci": "CI/CD",
        "build": "Build",
    }
    label = type_map.get(ctype, ctype.title())

    return ctype, body, label


def decision_hash(ctype: str, description: str, area: str) -> str:
    """Generate a content-based hash for dedup."""
    key = f"{ctype}:{area}:{description}".lower()
    return hashlib.md5(key.encode()).hexdigest()[:12]


def is_recent(ctype: str, area: str, max_age_minutes: int = 10) -> bool:
    """
    Check if a decision was recorded for this (ctype, area) in the last max_age_minutes.
    Returns True if recently recorded (skip to avoid spam).
    Only the (type, area) combination is deduplicated — different descriptions
    for the same area are still allowed if they add new information.
    """
    if not DEBOUNCE_FILE.exists():
        return False

    try:
        data = json.loads(DEBOUNCE_FILE.read_text())
    except Exception:
        return False

    cutoff = datetime.now() - timedelta(minutes=max_age_minutes)
    key = f"{ctype}:{area}"

    for entry in data.get("decisions", []):
        entry_time = datetime.fromisoformat(entry.get("timestamp", "1970-01-01"))
        entry_key = entry.get("key", "")

        if entry_key == key and entry_time > cutoff:
            return True

    return False


def record_recent(ctype: str, area: str, description: str):
    """Record this decision to debounce file so we don't record again soon."""
    data = {"decisions": []}
    if DEBOUNCE_FILE.exists():
        try:
            data = json.loads(DEBOUNCE_FILE.read_text())
        except Exception:
            data = {"decisions": []}

    # Keep only last 50 entries
    data["decisions"] = data.get("decisions", [])[-49:]
    data["decisions"].append({
        "timestamp": datetime.now().isoformat(),
        "key": f"{ctype}:{area}",
        "hash": decision_hash(ctype, description, area),
    })

    try:
        DEBOUNCE_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass  # best-effort


def record_decision(ctype: str, label: str, description: str, area: str) -> bool:
    """
    Record a decision to user_decisions.json.
    Returns True if recorded, False if skipped.
    """
    if os.environ.get("NEUTRON_DREAM_TEST") == "1":
        return False  # skip in test mode

    decision_text = f"{label} in {area}: {description}"

    try:
        from engine.user_decisions import record as record_fn
        result = record_fn(
            decision=decision_text,
            context=f"commit: {description[:80]} | files: {area}",
            project="NEUTRON-EVO-OS",
            outcome="accepted",
        )
        return result.get("status") == "recorded"
    except Exception:
        return False


def run() -> int:
    """
    Main entry point for pre-commit hook.
    Returns: 0 (always passes — decision recording is best-effort)
    """
    msg = get_commit_msg()
    files = get_changed_files()

    ctype, description, label = parse_commit(msg)
    if ctype is None or description is None:
        return 0

    area = summarize_area(files)

    # Debounce: skip if same (type, area) was recorded in last 10 minutes
    if is_recent(ctype, area):
        return 0

    # Record the decision
    recorded = record_decision(ctype, label, description, area)
    record_recent(ctype, area, description)

    if recorded:
        print(f"[auto-decision] Recorded: {label} in {area}")

    return 0  # never block on decision recording


if __name__ == "__main__":
    sys.exit(run())
