#!/usr/bin/env python3
"""
NEUTRON EVO OS — Checkpoint CLI
Wraps /checkpoint skill for CLI/hook invocation.
Usage:
    python3 checkpoint_cli.py [--handoff] [--focus "trading module"] [--task "description"]
"""
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
CHECKPOINT_SCRIPT = NEUTRON_ROOT / "skills" / "core" / "checkpoint" / "SKILL.md"
_CHECKPOINT_LOCK = MEMORY_DIR / ".checkpoint.lock"


def _write_atomic(path: Path, content: str):
    """Filelock + atomic write: prevents concurrent writes from corrupting checkpoint."""
    import filelock, tempfile, os as _os
    lock = filelock.FileLock(str(_CHECKPOINT_LOCK), timeout=10)
    with lock:
        fd = tempfile.NamedTemporaryFile(
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

# PII scrubbing patterns — ORDER MATTERS (specific first, general last)
_PII_PATTERNS = [
    # [KEY] first: specific prefix patterns (TOKEN=sk-xxxx, api_key=xxxx, etc.)
    (re.compile(r"(?i)(?:api[_-]?key|secret[_-]?key|token|password)\s*[:=]\s*['\"]?[\w\-]{16,}['\"]?"), "[KEY]"),
    # [KEY] standalone: bare API keys with sk- or similar prefixes
    (re.compile(r"(?i)\b(sk-[a-zA-Z0-9]{20,}|ghp_[a-zA-Z0-9]{20,}|xox[baprs]-[a-zA-Z0-9]{10,})\b"), "[KEY]"),
    # [CARD]: 16-digit card patterns
    (re.compile(r"\b\d{4}[\s-]?\d{4}[\s-]?\d{4}[\s-]?\d{4}\b"), "[CARD]"),
    # [EMAIL]
    (re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}"), "[EMAIL]"),
    # [PHONE]: clear phone patterns only (with word boundary guards)
    (re.compile(r"(?<![a-zA-Z])\+?[0-9][0-9\s\-().]{7,}[0-9](?![a-zA-Z0-9])"), "[PHONE]"),
]


def redact_pii(text: str) -> str:
    """Remove PII patterns from text before writing to disk."""
    if not text:
        return text
    result = text
    for pattern, replacement in _PII_PATTERNS:
        result = pattern.sub(replacement, result)
    return result


def get_latest_checkpoint() -> Optional[dict]:
    """Read today's checkpoint if it exists."""
    today = datetime.now().strftime("%Y-%m-%d")
    checkpoint_path = MEMORY_DIR / f"{today}.md"
    if checkpoint_path.exists():
        content = checkpoint_path.read_text()
        # Simple parse: extract state from markdown
        return {"path": str(checkpoint_path), "content": content}
    return None


def write_checkpoint(
    task: str = "session in progress",
    focus: str = "",
    status: str = "in_progress",
    blockers: list = None,
    next_steps: list = None,
    decisions: list = None,
    notes: str = "",
    modified_files: list = None,
    created_files: list = None,
    last_action: str = "",
    output: str = "",
    confidence: str = "medium",
) -> dict:
    """
    Write a structured checkpoint to memory/{date}.md.
    Appends to existing checkpoint or creates new one.
    """
    MEMORY_DIR.mkdir(exist_ok=True)

    today = datetime.now().strftime("%Y-%m-%d")
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    checkpoint_path = MEMORY_DIR / f"{today}.md"

    blockers = blockers or []
    next_steps = next_steps or []
    decisions = decisions or []
    modified_files = modified_files or []
    created_files = created_files or []

    # Redact PII from all user-supplied text fields before writing
    task = redact_pii(task)
    focus = redact_pii(focus)
    notes = redact_pii(notes)
    status = redact_pii(status)
    last_action = redact_pii(last_action)
    output = redact_pii(output)
    blockers = [redact_pii(b) for b in blockers]
    next_steps = [redact_pii(s) for s in next_steps]
    decisions = [redact_pii(d) for d in decisions]

    # Parse existing checkpoint to preserve header
    existing = ""
    if checkpoint_path.exists():
        content = checkpoint_path.read_text()
        # Keep existing content, we'll append a new section
        existing = content

    checkpoint_entry = f"""
---

## Checkpoint — {timestamp}

### State
- **Status**: {status}
- **Task**: {task}
- **Focus**: {focus}
- **Confidence**: {confidence}

### Files
- **Modified**: {', '.join(modified_files) if modified_files else '(none)'}
- **Created**: {', '.join(created_files) if created_files else '(none)'}
- **Last Action**: {last_action}

### Blockers
{chr(10).join(f'- [ ] {b}' for b in blockers) if blockers else '- (none)'}

### Next Steps (priority order)
{chr(10).join(f'{i+1}. {s}' for i, s in enumerate(next_steps)) if next_steps else '- (none)'}

### Decisions Made
{chr(10).join(f'- {d}' for d in decisions) if decisions else '- (none)'}

### Notes
{notes if notes else '(none)'}
"""

    if existing:
        # Find last "---" separator and insert before it (or append)
        if "---" in existing:
            last_sep = existing.rfind("---")
            new_content = existing[:last_sep] + checkpoint_entry + "\n\n---\n"
        else:
            new_content = existing + checkpoint_entry
    else:
        new_content = f"""# Checkpoint — {today}

> NEUTRON EVO OS v4.0.0 | Auto-checkpoint enabled
> This file tracks session state for context compression survival.

"""
        new_content += f"""## Session Info
- **Started**: {timestamp}
- **Root**: {NEUTRON_ROOT}

"""
        new_content += checkpoint_entry

    # Atomic write under filelock — prevents concurrent writes from interleaving
    _write_atomic(checkpoint_path, new_content)

    return {
        "status": "saved",
        "path": str(checkpoint_path),
        "timestamp": timestamp,
        "task": task,
        "focus": focus,
        "size_bytes": len(new_content),
    }


def run_dream_cycle() -> dict:
    """Trigger Dream Cycle after checkpoint save."""
    try:
        from engine.dream_engine import dream_cycle

        result = dream_cycle()
        return {"dream_status": result.get("status", "unknown"), "dream_result": result}
    except Exception as e:
        return {"dream_status": "error", "error": str(e)}


def main():
    parser = argparse.ArgumentParser(description="NEUTRON EVO OS — Checkpoint CLI")
    parser.add_argument("--task", "-t", default="session in progress", help="Current task description")
    parser.add_argument("--focus", "-f", default="", help="Focus area (e.g. 'trading module')")
    parser.add_argument(
        "--status",
        "-s",
        default="in_progress",
        choices=["in_progress", "paused", "blocked", "complete"],
        help="Session status",
    )
    parser.add_argument(
        "--blocker", "-b", action="append", default=[], dest="blockers", help="Blocker description (repeatable)"
    )
    parser.add_argument(
        "--next", "-n", action="append", default=[], dest="next_steps", help="Next step (repeatable)"
    )
    parser.add_argument(
        "--decision", "-d", action="append", default=[], dest="decisions", help="Decision made (repeatable)"
    )
    parser.add_argument("--notes", default="", help="Additional notes")
    parser.add_argument("--modified", action="append", default=[], dest="modified_files", help="Modified file")
    parser.add_argument("--created", action="append", default=[], dest="created_files", help="Created file")
    parser.add_argument("--last-action", default="", help="Last action description")
    parser.add_argument("--output", default="", help="Last action output summary")
    parser.add_argument(
        "--confidence", "-c", default="medium", choices=["high", "medium", "low"], help="Agent confidence"
    )
    parser.add_argument(
        "--handoff", action="store_true", help="Handoff mode: checkpoint + dream cycle (for hook use)"
    )
    parser.add_argument(
        "--read", action="store_true", help="Read latest checkpoint instead of writing"
    )

    args = parser.parse_args()

    if args.read:
        ckpt = get_latest_checkpoint()
        if ckpt:
            print(json.dumps(ckpt, indent=2, ensure_ascii=False))
        else:
            print(json.dumps({"status": "no_checkpoint", "message": "No checkpoint found for today"}))
        return

    result = write_checkpoint(
        task=args.task,
        focus=args.focus,
        status=args.status,
        blockers=args.blockers,
        next_steps=args.next_steps,
        decisions=args.decisions,
        notes=args.notes,
        modified_files=args.modified_files,
        created_files=args.created_files,
        last_action=args.last_action,
        output=args.output,
        confidence=args.confidence,
    )

    print(json.dumps(result, indent=2, ensure_ascii=False))

    if args.handoff:
        print("\n--- Dream Cycle ---")
        dream_result = run_dream_cycle()
        print(json.dumps(dream_result, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
