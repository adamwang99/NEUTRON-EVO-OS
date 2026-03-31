"""
Memory Skill — Logic Module
run_memory(task, context) → {status, output, ci_delta}

Actions (via context["action"]):
  - log     : append session entry to memory/YYYY-MM-DD.md
  - archive : copy file to memory/archived/ (timestamped)
  - search  : search over memory/ directory
  - dream   : trigger Dream Cycle (delegate to dream_engine.dream_cycle())
  - status  : show memory/ directory statistics

CI rewards: log=+2, archive=+3, dream=+10, failure=-5
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
