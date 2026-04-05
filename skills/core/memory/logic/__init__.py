"""
Memory Skill — Logic Module
run_memory(task, context) → {status, output, ci_delta}

Actions (via context["action"]):
  - log      : append session entry to memory/YYYY-MM-DD.md
  - archive  : copy file to memory/archived/ (timestamped)
  - search   : search over memory/ directory
  - dream    : trigger Dream Cycle (delegate to dream_engine.dream_cycle())
  - status   : show memory/ directory statistics
  - learned  : add entry to memory/LEARNED.md, or search by tag/keyword
  - decision : record or query key decisions (user_decisions.json)
  - shipment : record or query shipped projects (shipments.json)

CI rewards: log=+2, archive=+3, dream=+10, learned=+5, decision=+3, shipment=+10, failure=-5
Does NOT replace MemoryOS — keeps both systems separate.
"""
from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path
from datetime import datetime

# Levels: logic/__init__.py → memory/ → core/ → skills/ → repo root
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent.parent)
))
MEMORY_DIR = _NEUTRON_ROOT / "memory"
ARCHIVED_DIR = MEMORY_DIR / "archived"

# PII patterns (same as checkpoint_cli — shared concern)
_PII_PATTERNS = [
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    (re.compile(r"\+?[0-9][0-9\s\-()]{7,}[0-9]"), "[PHONE]"),
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARD]"),
    (re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key|token|password)\s*[:=]\s*['\"]?[\w\-]{16,}['\"]?",), "[KEY]"),
]


def _redact(text: str) -> str:
    """Redact PII from text before writing to disk."""
    if not text:
        return text
    result = text
    for pattern, replacement in _PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def run_memory(task: str, context: dict = None) -> dict:
    context = context or {}
    action = context.get("action", "log")

    if action == "log":
        return _write_daily_log(task, context)
    elif action == "archive":
        return _archive_file(context)
    elif action == "search":
        return _search_memories(context)
    elif action == "dream":
        return _trigger_dream_cycle()
    elif action == "status":
        return _memory_status()
    elif action == "learned":
        return _learned(task, context)
    elif action == "decision":
        return _decision(task, context)
    elif action == "shipment":
        return _shipment(task, context)
    else:
        return {"status": "error", "output": f"Unknown action: '{action}'", "ci_delta": 0}


def _write_daily_log(task: str, context: dict) -> dict:
    MEMORY_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = MEMORY_DIR / f"{today}.md"
    ts = datetime.now().strftime("%H:%M")
    ci_delta = context.get("ci_delta", 2)
    entry = (
        f"\n## [{ts}] — Task: {task[:80]}\n"
        f"- Action: {context.get('action_detail', task)}\n"
        f"- Outcome: {context.get('outcome', 'completed')}\n"
        f"- CI delta: {ci_delta:+.0f}\n"
        f"- Notes: {_redact(context.get('notes', ''))}\n"
    )
    content = log_path.read_text() if log_path.exists() else f"# {today}\n"
    log_path.write_text(content + entry + "\n")
    return {"status": "ok", "output": f"Logged to {log_path.name}", "ci_delta": ci_delta}


def _archive_file(context: dict) -> dict:
    file_path = context.get("file_path")
    if not file_path:
        return {"status": "error", "output": "file_path required in context", "ci_delta": 0}
    p = Path(file_path)
    if not p.exists():
        return {"status": "error", "output": f"Not found: {file_path}", "ci_delta": 0}
    ARCHIVED_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    dest = ARCHIVED_DIR / f"{p.stem}_{ts}{p.suffix}"
    shutil.copy2(p, dest)
    return {"status": "archived", "output": f"Archived to {dest.name}", "ci_delta": 3}


def _search_memories(context: dict) -> dict:
    query = context.get("query", "")
    if not query:
        return {"status": "error", "output": "query required in context", "ci_delta": 0}
    results = []
    if MEMORY_DIR.exists():
        for md in MEMORY_DIR.rglob("*.md"):
            try:
                if query.lower() in md.read_text(errors="ignore").lower():
                    results.append(str(md.relative_to(_NEUTRON_ROOT)))
            except Exception:
                continue
    return {
        "status": "ok",
        "output": f"Found {len(results)} match(es) for '{query}'",
        "results": results,
        "ci_delta": 0,
    }


def _trigger_dream_cycle() -> dict:
    """
    Trigger Dream Cycle via subprocess.
    Uses a temp script file instead of inline code to prevent injection
    via NEUTRON_ROOT path containing special characters.
    """
    env = dict(os.environ)
    env["NEUTRON_ROOT"] = str(_NEUTRON_ROOT)
    # Write script to temp file — NEUTRON_ROOT path is passed as env var, not embedded in code
    import tempfile
    script_content = (
        "import sys, os, json\n"
        f"sys.path.insert(0, os.environ['NEUTRON_ROOT'])\n"
        "from engine.dream_engine import dream_cycle\n"
        "print(dream_cycle(json_output=True))\n"
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
        f.write(script_content)
        script_path = f.name
    try:
        result = subprocess.run(
            [sys.executable, script_path],
            capture_output=True, text=True, timeout=60, env=env,
        )
        if result.returncode == 0:
            return {"status": "dream_complete", "output": result.stdout.strip(), "ci_delta": 10}
        return {"status": "error", "output": result.stderr.strip() or "Dream Cycle failed", "ci_delta": -5}
    finally:
        import os as _os
        _os.unlink(script_path)


def _memory_status() -> dict:
    total = len(list(MEMORY_DIR.rglob("*.md"))) if MEMORY_DIR.exists() else 0
    archived = 0
    if ARCHIVED_DIR.exists():
        archived = len(list(ARCHIVED_DIR.rglob("*")))
    return {"status": "ok", "output": f"memories={total}, archived={archived}", "ci_delta": 0}


def _learned(task: str, context: dict) -> dict:
    """
    Add or search entries in memory/LEARNED.md.
    Sub-actions via context["sub_action"]: "add", "search", "list"
    Required for "add": context["symptom"], context["root_cause"],
                    context["fix"], context["tags"]
    """
    learned_path = MEMORY_DIR / "LEARNED.md"
    sub = context.get("sub_action", "list")
    today = datetime.now().strftime("%Y-%m-%d")

    if sub == "add":
        symptom = context.get("symptom", "")
        root = context.get("root_cause", "")
        fix = context.get("fix", "")
        tags = context.get("tags", "")
        lesson = context.get("lesson", "")

        if not (symptom and root and fix):
            return {
                "status": "error",
                "output": "learned add requires: symptom, root_cause, fix",
                "ci_delta": -3,
            }

        # Build entry
        entry = (
            f"\n## [{today}] Bug: {task[:80]}\n"
            f"- **Symptom:** {symptom}\n"
            f"- **Root cause:** {root}\n"
            f"- **Fix:** {fix}\n"
            f"- **Tags:** {tags or '#bug'}\n"
            f"- **Lesson:** {lesson}\n"
        )

        content = _read_or_init_learned(learned_path)
        content += entry + "\n"
        learned_path.write_text(content)
        return {"status": "added", "output": f"Entry added to LEARNED.md", "ci_delta": 5}

    elif sub == "search":
        query = context.get("query", "") or task
        return _search_learned(learned_path, query)

    else:  # list
        if not learned_path.exists():
            return {"status": "ok", "output": "LEARNED.md is empty", "ci_delta": 0}
        count = sum(1 for line in learned_path.read_text().splitlines()
                    if line.startswith("## ["))
        return {
            "status": "ok",
            "output": f"LEARNED.md: {count} bug fix(es) recorded",
            "ci_delta": 0,
        }


def _read_or_init_learned(path: Path) -> str:
    """Read existing LEARNED.md or create the header."""
    header = (
        "# LEARNED.md — Bug Fixes & Pattern Database\n\n"
        "> Every bug fix is a permanent asset. Every mistake is a lesson learned.\n"
        "> ∫f(t)dt — Functional Credibility Over Institutional Inertia\n\n---\n\n"
    )
    if path.exists():
        return path.read_text()
    path.write_text(header)
    return header


def _search_learned(path: Path, query: str) -> dict:
    """Grep LEARNED.md for query (tag or keyword)."""
    if not path.exists():
        return {"status": "ok", "output": "LEARNED.md not found", "results": [], "ci_delta": 0}
    lines = path.read_text().splitlines()
    matching = []
    for i, line in enumerate(lines):
        if query.lower() in line.lower():
            # Grab context around this line
            start = max(0, i - 2)
            snippet = "\n".join(lines[start:i + 5])
            matching.append(snippet)
    return {
        "status": "ok",
        "output": f"Found {len(matching)} match(es) for '{query}'",
        "results": matching,
        "ci_delta": 0,
    }


def _decision(task: str, context: dict) -> dict:
    """
    Record or list decisions in memory/user_decisions.json.
    Sub-actions via context["sub_action"]: "add", "list"
    Required for "add": context["decision"], context["context"]
    """
    import json as _json

    decisions_path = MEMORY_DIR / "user_decisions.json"

    sub = context.get("sub_action", "list")

    if sub == "add":
        decisions = []
        if decisions_path.exists():
            try:
                decisions = _json.loads(decisions_path.read_text())
            except Exception:
                pass

        new_id = (max((d["id"] for d in decisions), default=0)) + 1
        entry = {
            "id": new_id,
            "timestamp": datetime.now().isoformat(),
            "decision": task or context.get("decision", ""),
            "context": context.get("context", ""),
            "outcome": "pending",
        }
        decisions.append(entry)
        decisions_path.write_text(_json.dumps(decisions, indent=2))
        return {"status": "added", "output": f"Decision #{new_id} recorded", "ci_delta": 3}

    else:  # list
        if not decisions_path.exists():
            return {"status": "ok", "output": "No decisions recorded yet", "ci_delta": 0}
        try:
            decisions = _json.loads(decisions_path.read_text())
        except Exception:
            return {"status": "error", "output": "Corrupted decisions file", "ci_delta": -3}
        pending = [d for d in decisions if d.get("outcome") == "pending"]
        applied = [d for d in decisions if d.get("outcome") == "applied"]
        return {
            "status": "ok",
            "output": f"{len(decisions)} decision(s) — {len(pending)} pending, {len(applied)} applied",
            "decisions": decisions[-10:],  # last 10
            "ci_delta": 0,
        }


def _shipment(task: str, context: dict) -> dict:
    """
    Record or list shipments in memory/shipments.json.
    Sub-actions via context["sub_action"]: "add", "list"
    Required for "add": context["rating"] (1-5), context["steps_completed"]
    """
    import json as _json

    shipments_path = MEMORY_DIR / "shipments.json"

    sub = context.get("sub_action", "list")

    if sub == "add":
        shipments = []
        if shipments_path.exists():
            try:
                shipments = _json.loads(shipments_path.read_text()).get("shipments", [])
            except Exception:
                pass

        new_id = (max((s["id"] for s in shipments), default=0)) + 1
        entry = {
            "id": new_id,
            "timestamp": datetime.now().isoformat(),
            "project": task,
            "complexity": context.get("complexity", "MEDIUM"),
            "steps_completed": context.get("steps_completed", []),
            "time_to_ship_minutes": context.get("time_minutes", 0),
            "outcome": "shipped",
            "rating": context.get("rating"),
            "rating_notes": context.get("notes", ""),
            "rating_timestamp": datetime.now().isoformat(),
        }
        shipments.append(entry)
        data = {"shipments": shipments, "counter": new_id}
        shipments_path.write_text(_json.dumps(data, indent=2))
        return {"status": "shipped", "output": f"Shipment #{new_id}: {task}", "ci_delta": 10}

    else:  # list
        if not shipments_path.exists():
            return {"status": "ok", "output": "No shipments recorded yet", "ci_delta": 0}
        try:
            data = _json.loads(shipments_path.read_text())
            shipments = data.get("shipments", [])
        except Exception:
            return {"status": "error", "output": "Corrupted shipments file", "ci_delta": -3}
        rated = [s for s in shipments if s.get("rating")]
        avg = sum(s["rating"] for s in rated) / len(rated) if rated else 0
        return {
            "status": "ok",
            "output": (
                f"{len(shipments)} shipment(s) — "
                f"{len(rated)} rated — avg rating: {avg:.1f}/5"
            ),
            "shipments": shipments[-10:],  # last 10
            "ci_delta": 0,
        }
