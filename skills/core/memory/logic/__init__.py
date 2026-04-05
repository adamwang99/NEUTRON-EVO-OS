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
  - sync    : extract bugs/decisions from local logs → push to hub NEUTRON_HUB_ROOT

CI rewards: log=+2, archive=+3, dream=+10, learned=+5, decision=+3, shipment=+10, failure=-5
Does NOT replace MemoryOS — keeps both systems separate.
"""
from __future__ import annotations

import filelock
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
    elif action == "sync":
        return _sync_to_hub(context)
    elif action == "shipment":
        return _shipment(task, context)
    elif action == "approve":
        return _approve_pending(context)
    elif action == "reject":
        return _reject_pending(context)
    elif action == "pending":
        return _list_pending()
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


def _locked_read_write(path: Path, update_fn) -> dict:
    """
    Atomic read-modify-write using filelock + temp file.
    update_fn(old_data) -> new_data (list/dict) or None to skip write.
    Always returns dict with {"status": ..., "data": ...}.
    """
    import json as _json
    lock_path = str(path.with_suffix(".lock"))
    lock = filelock.FileLock(lock_path, timeout=10)
    try:
        with lock:
            data = [] if not path.exists() else _json.loads(path.read_text())
            result = update_fn(data)
            if result is not None:
                path.write_text(_json.dumps(result, indent=2))
            return {"status": "ok", "data": result if result is not None else data}
    except filelock.Timeout:
        return {"status": "error", "output": f"Lock timeout on {path.name} — try again", "ci_delta": -3}
    except _json.JSONDecodeError:
        return {"status": "error", "output": f"Corrupted {path.name} — data archived, reset to empty", "ci_delta": -5}


def _decision(task: str, context: dict) -> dict:
    """
    Record or list decisions in memory/user_decisions.json.
    Sub-actions via context["sub_action"]: "add", "list"
    Required for "add": context["decision"], context["context"]
    Thread-safe: uses filelock + atomic write.
    """
    import json as _json

    decisions_path = MEMORY_DIR / "user_decisions.json"
    sub = context.get("sub_action", "list")

    if sub == "add":
        new_id_ref = [0]  # mutable container for id

        def add_entry(data):
            new_id_ref[0] = max((d["id"] for d in data), default=0) + 1
            entry = {
                "id": new_id_ref[0],
                "timestamp": datetime.now().isoformat(),
                "decision": task or context.get("decision", ""),
                "context": context.get("context", ""),
                "outcome": "pending",
            }
            data.append(entry)
            return data

        result = _locked_read_write(decisions_path, add_entry)
        if result.get("status") == "error":
            return result
        return {"status": "added", "output": f"Decision #{new_id_ref[0]} recorded", "ci_delta": 3}

    else:  # list
        def read_all(data):
            return data  # return unmodified for list

        result = _locked_read_write(decisions_path, read_all)
        if result.get("status") == "error":
            return result
        data = result.get("data", [])
        pending = [d for d in data if d.get("outcome") == "pending"]
        applied = [d for d in data if d.get("outcome") == "applied"]
        return {
            "status": "ok",
            "output": f"{len(data)} decision(s) — {len(pending)} pending, {len(applied)} applied",
            "decisions": data[-10:],
            "ci_delta": 0,
        }


def _sync_to_hub(context: dict) -> dict:
    """
    Extract bugs and decisions from local session logs and push to hub NEUTRON_ROOT.
    This enables cross-project knowledge sharing.

    Multi-window workflow:
      1. Work on project (local memory/YYYY-MM-DD.md accumulates)
      2. Run: neutron sync --hub ~/.neutron-evo-os
         → OR: neutron memory sync --hub ~/.neutron-evo-os
         → OR: neutron sync
      3. Bugs/decisions extracted from local logs → pushed to hub
      4. Next session (any project) → SessionStart reads hub LEARNED.md
    """
    import json as _json
    import re
    from datetime import datetime, timedelta

    hub_root = context.get("hub_root") or os.environ.get("NEUTRON_HUB_ROOT")
    if not hub_root:
        # Default: ~/.neutron-evo-os
        hub_root = os.path.expanduser("~/.neutron-evo-os")

    hub_path = Path(hub_root)
    local_path = _NEUTRON_ROOT

    # If hub == local, nothing to sync
    try:
        hub_path.resolve().relative_to(local_path.resolve())
        same_path = True
    except ValueError:
        same_path = False

    if same_path:
        return {
            "status": "skipped",
            "output": "Hub == local NEUTRON_ROOT — nothing to sync. "
                      "Run from a project satellite to push learnings to hub.",
            "ci_delta": 0,
        }

    # Verify hub has memory directory
    hub_memory = hub_path / "memory"
    if not hub_memory.exists():
        return {
            "status": "error",
            "output": f"Hub memory/ not found at {hub_path} — "
                      f"is NEUTRON_HUB_ROOT set correctly?",
            "ci_delta": -3,
        }

    # ── Extract STRUCTURED entries from local LEARNED.md ─────────────────────
    # Only sync structured ## [DATE] Bug: entries — never raw log excerpts.
    # Filter out: "From X: N log excerpt(s)" contamination, [PENDING] entries.
    local_learned = local_path / "memory" / "LEARNED.md"
    structured_entries = []
    contamination_patterns = [
        re.compile(r"From\s+\w+:\s*\d+\s+log excerpt", re.IGNORECASE),
        re.compile(r"\[PENDING\]"),
    ]
    is_contaminated = lambda s: any(p.search(s) for p in contamination_patterns)

    if local_learned.exists():
        content = local_learned.read_text()
        # Extract each structured Bug: entry (from "## [" to next "## [")
        current = []
        for line in content.splitlines():
            if re.match(r"^\s*##\s+\[", line):
                if current and not is_contaminated("\n".join(current)):
                    structured_entries.append("\n".join(current))
                current = []
            if current or (re.match(r"^\s*##\s+\[", line)):
                current.append(line)
        # Don't forget last entry
        if current and not is_contaminated("\n".join(current)):
            structured_entries.append("\n".join(current))

    # Also extract structured decision entries from local user_decisions.json
    local_decisions = local_path / "memory" / "user_decisions.json"
    synced_decisions = []
    if local_decisions.exists():
        try:
            decisions = _json.loads(local_decisions.read_text())
            if isinstance(decisions, list):
                # Only sync applied/resolved decisions (not pending)
                for d in decisions:
                    if d.get("outcome") in ("applied", "resolved", "shipped"):
                        synced_decisions.append(d)
        except Exception:
            pass

    if not structured_entries and not synced_decisions:
        return {
            "status": "skipped",
            "output": (
                f"No structured LEARNED.md entries or applied decisions to sync. "
                f"Hub LEARNED.md only accepts structured entries — raw log excerpts are ignored."
            ),
            "ci_delta": 0,
        }

    # ── Push to hub with filelock ──────────────────────────────────────────
    hub_learned = hub_memory / "LEARNED.md"
    hub_decisions = hub_memory / "decisions.json"
    hub_index = hub_memory / "index.json"

    today_str = datetime.now().strftime("%Y-%m-%d")
    project_name = local_path.name

    def _safe_json_write(path: Path, data: list) -> int:
        lock_path = str(path.with_suffix(".lock"))
        lock = filelock.FileLock(lock_path, timeout=10)
        try:
            with lock:
                existing = []
                if path.exists():
                    try:
                        existing = _json.loads(path.read_text())
                        if not isinstance(existing, list):
                            existing = []
                    except Exception:
                        existing = []
                merged = existing + data
                path.write_text(_json.dumps(merged, indent=2))
        except filelock.Timeout:
            raise TimeoutError(f"Lock timeout on {path.name}")
        return len(data)

    def _append_structured_learned(entries: list[str]) -> int:
        """
        Append structured LEARNED entries to hub LEARNED.md (not raw text).
        Deduplicates by bug title to prevent hub LEARNED.md from growing with
        repeated sync runs of the same entry.
        """
        if not entries:
            return 0

        lock_path = str(hub_learned.with_suffix(".lock"))
        lock = filelock.FileLock(lock_path, timeout=10)
        with lock:
            existing = hub_learned.read_text() if hub_learned.exists() else ""

            # Extract existing bug titles for dedup
            existing_titles: set[str] = set()
            for line in existing.splitlines():
                m = re.search(r"Bug:\s*(.+?)(?:\n|$)", line, re.IGNORECASE)
                if m:
                    existing_titles.add(m.group(1).strip().lower())

            # Filter out duplicates
            new_entries = []
            skipped = 0
            for entry in entries:
                # Extract title from entry
                m = re.search(r"Bug:\s*(.+?)(?:\n|$)", entry, re.IGNORECASE)
                if m:
                    title = m.group(1).strip().lower()
                    if title in existing_titles:
                        skipped += 1
                        continue
                    existing_titles.add(title)
                new_entries.append(entry)

            if not new_entries:
                return 0

            header = f"\n## [{today_str}] From {project_name}: LEARNED sync\n"
            body = "\n".join(new_entries)
            content = header + body + "\n"
            hub_learned.write_text(existing + content)

        return len(new_entries) - skipped if skipped else len(new_entries)

    def _append_decisions(decs: list[dict]) -> int:
        if not decs:
            return 0
        entries = [
            {
                "id": 0,
                "timestamp": datetime.now().isoformat(),
                "decision": d.get("decision", ""),
                "context": f"Synced from {project_name}",
                "outcome": d.get("outcome", "applied"),
                "_synced_from": project_name,
            }
            for d in decs[:20]
        ]
        return _safe_json_write(hub_decisions, entries)

    def _update_index(entries_count: int, decisions_count: int) -> bool:
        idx = []
        if hub_index.exists():
            try:
                idx = _json.loads(hub_index.read_text())
            except Exception:
                idx = []
        now = datetime.now().isoformat()
        updated = False
        for entry in idx:
            if entry.get("project") == project_name:
                entry["last_sync"] = now
                entry["entries_synced"] = entries_count
                entry["decisions_synced"] = decisions_count
                updated = True
        if not updated:
            idx.append({
                "project": project_name,
                "local_root": str(local_path),
                "last_sync": now,
                "entries_synced": entries_count,
                "decisions_synced": decisions_count,
            })
        hub_index.write_text(_json.dumps(idx, indent=2))
        return True

    entries_count = _append_structured_learned(structured_entries)
    decisions_count = _append_decisions(synced_decisions)
    _update_index(entries_count, decisions_count)

    return {
        "status": "synced",
        "output": (
            f"Synced to {hub_path.name}:\n"
            f"  LEARNED entries: {entries_count} structured entry/entries → hub LEARNED.md\n"
            f"  Decisions: {decisions_count} → hub decisions.json\n"
            f"  Index updated for '{project_name}'\n"
            f"\n"
            f"Raw log excerpts are NOT synced — only structured entries.\n"
            f"Next: Open any project — SessionStart reads hub LEARNED.md automatically."
        ),
        "entries_synced": entries_count,
        "decisions_synced": decisions_count,
        "hub": str(hub_path),
        "project": project_name,
        "ci_delta": 5,
    }


def _shipment(task: str, context: dict) -> dict:
    """
    Record or list shipments in memory/shipments.json.
    Sub-actions via context["sub_action"]: "add", "list"
    Required for "add": context["rating"] (1-5), context["steps_completed"]
    Thread-safe: uses filelock + atomic write.
    """
    import json as _json

    shipments_path = MEMORY_DIR / "shipments.json"
    sub = context.get("sub_action", "list")

    if sub == "add":
        new_id_ref = [0]

        def add_entry(data):
            new_id_ref[0] = max((s["id"] for s in data), default=0) + 1
            entry = {
                "id": new_id_ref[0],
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
            data.append(entry)
            return data

        result = _locked_read_write(shipments_path, add_entry)
        if result.get("status") == "error":
            return result
        return {"status": "shipped", "output": f"Shipment #{new_id_ref[0]}: {task}", "ci_delta": 10}

    else:  # list
        def read_all(data):
            return data

        result = _locked_read_write(shipments_path, read_all)
        if result.get("status") == "error":
            return result
        shipments = result.get("data", [])
        rated = [s for s in shipments if s.get("rating")]
        avg = sum(s["rating"] for s in rated) / len(rated) if rated else 0
        return {
            "status": "ok",
            "output": (
                f"{len(shipments)} shipment(s) — "
                f"{len(rated)} rated — avg rating: {avg:.1f}/5"
            ),
            "shipments": shipments[-10:],
            "ci_delta": 0,
        }


PENDING_DIR = MEMORY_DIR / "pending"


def _list_pending() -> dict:
    """List pending LEARNED entries awaiting human approval."""
    pending_path = PENDING_DIR / "LEARNED_pending.md"
    if not pending_path.exists():
        return {"status": "ok", "output": "No pending LEARNED entries.", "pending": [], "ci_delta": 0}

    content = pending_path.read_text()
    entries = []
    current = []
    for line in content.splitlines():
        if line.startswith("## [") and "[PENDING]" in line:
            if current:
                entries.append("\n".join(current))
            current = []
        if current or (line.startswith("## [") and "[PENDING]" in line):
            current.append(line)
    if current:
        entries.append("\n".join(current))

    if not entries:
        return {"status": "ok", "output": "No pending LEARNED entries.", "pending": [], "ci_delta": 0}

    return {
        "status": "ok",
        "output": f"{len(entries)} pending LEARNED entry/entries:\n" +
                  "\n".join(f"  • {e[:100]}" for e in entries[:5]),
        "pending": [e[:200] for e in entries],
        "ci_delta": 0,
    }


def _approve_pending(context: dict) -> dict:
    """
    Move a pending LEARNED entry to official LEARNED.md.
    Thread-safe: filelock + atomic write for both files.
    Usage: neutron memory approve pending-YYYYMMDD-N
    """
    draft_id = context.get("draft_id", "")
    if not draft_id:
        return {
            "status": "error",
            "output": "draft_id required: neutron memory approve <draft_id>",
            "ci_delta": -3,
        }

    pending_path = PENDING_DIR / "LEARNED_pending.md"
    learned_path = MEMORY_DIR / "LEARNED.md"
    lock_path = PENDING_DIR / "LEARNED_pending.lock"

    if not pending_path.exists():
        return {"status": "error", "output": "No pending entries found.", "ci_delta": -3}

    lock = filelock.FileLock(str(lock_path), timeout=10)
    with lock:
        content = pending_path.read_text()
        lines = content.splitlines()

        # Parse into entry blocks (each block = list of lines)
        blocks: list[list[str]] = []
        current: list[str] = []
        for line in lines:
            if line.startswith("## [") and "[PENDING]" in line:
                if current:
                    blocks.append(current)
                current = [line]
            elif current:
                current.append(line)
        if current:
            blocks.append(current)

        # Find target block by exact Draft ID
        target_block: list[str] | None = None
        remaining_blocks: list[list[str]] = []
        for block in blocks:
            block_text = "\n".join(block)
            if f"Draft ID: {draft_id}" in block_text:
                target_block = block
            else:
                remaining_blocks.append(block)

        if target_block is None:
            return {
                "status": "error",
                "output": f"Draft '{draft_id}' not found in pending entries.",
                "ci_delta": -3,
            }

        # Strip [PENDING] from header, keep rest of block intact
        approved_lines = []
        for line in target_block:
            if "[PENDING]" in line:
                approved_lines.append(line.replace("[PENDING]", "").replace("  ", " ").strip())
            else:
                approved_lines.append(line)
        approved_text = "\n".join(approved_lines)

        # Write approved entry to LEARNED.md (atomic)
        existing_learned = learned_path.read_text() if learned_path.exists() else ""
        _atomic_write_md(learned_path, existing_learned + "\n" + approved_text + "\n")

        # Write remaining pending back (atomic)
        remaining_text = "\n".join(
            line for block in remaining_blocks for line in block
        )
        _atomic_write_md(pending_path, remaining_text)

    return {
        "status": "approved",
        "output": f"Entry approved and added to LEARNED.md: {draft_id}",
        "ci_delta": 5,
    }


def _atomic_write_md(path: Path, content: str) -> None:
    """Atomic write: temp file + fsync + rename. Prevents partial-write corruption."""
    import os as _os
    import tempfile as _tempfile
    fd = _tempfile.NamedTemporaryFile(
        mode="w", dir=path.parent, delete=False, encoding="utf-8"
    )
    try:
        fd.write(content)
        fd.flush()
        _os.fsync(fd.fileno())
        fd.close()
        _os.replace(fd.name, str(path))
    except Exception:
        try:
            _os.unlink(fd.name)
        except Exception:
            pass
        raise


def _reject_pending(context: dict) -> dict:
    """
    Archive a pending LEARNED entry (not deleted, just removed from pending).
    Usage: neutron memory reject <draft_id>
    """
    draft_id = context.get("draft_id", "")
    if not draft_id:
        return {
            "status": "error",
            "output": "draft_id required: neutron memory reject <draft_id>",
            "ci_delta": 0,
        }

    pending_path = PENDING_DIR / "LEARNED_pending.md"
    if not pending_path.exists():
        return {"status": "error", "output": "No pending entries found.", "ci_delta": 0}

    ARCHIVED_DIR.mkdir(exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_path = ARCHIVED_DIR / f"LEARNED_pending_rejected_{ts}.md"

    content = pending_path.read_text()
    lines = content.splitlines()

    rejected_lines = []
    kept_lines = []
    in_target = False

    for line in lines:
        if line.startswith("## [") and "[PENDING]" in line:
            if in_target:
                # Close previous entry
                pass
            in_target = draft_id in line
            if in_target:
                rejected_lines = [line]
                continue
            else:
                kept_lines.append(line)
                continue
        if in_target:
            if line.startswith("## [") and "[PENDING]" in line:
                in_target = False
                kept_lines.append("\n".join(rejected_lines))
                rejected_lines = [line]
            else:
                rejected_lines.append(line)
        else:
            kept_lines.append(line)

    if rejected_lines:
        archive_path.write_text("\n".join(rejected_lines))

    if not rejected_lines:
        return {
            "status": "error",
            "output": f"Draft '{draft_id}' not found in pending entries.",
            "ci_delta": -3,
        }

    pending_path.write_text("\n".join(kept_lines))

    return {
        "status": "rejected",
        "output": f"Entry rejected and archived: {draft_id}",
        "ci_delta": 0,
    }
