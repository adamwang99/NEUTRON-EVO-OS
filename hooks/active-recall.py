#!/usr/bin/env python3
"""
NEUTRON EVO OS — Active Recall: LEARNED Pattern Matcher

Run by PreToolUse hook before every file Edit/Write.
Greps memory/LEARNED.md for bug patterns relevant to the file being modified.

Dual-output strategy:
  1. stderr  → Claude Code transcript (visible to user immediately)
  2. .claude/.active_recall.json → injected into next skill context
     (NEUTRON auto-includes session JSON files in context at startup)

This makes warnings TRULY "active" — they appear before coding decisions,
not just after the fact in transcript logs.
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path
from datetime import datetime

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
LEARNED_FILE = MEMORY_DIR / "LEARNED.md"
RECALL_CACHE = NEUTRON_ROOT / ".claude" / ".active_recall.json"

# Stopwords: filter out noise from task keyword extraction
STOPWORDS = {
    "the", "this", "that", "with", "from", "have", "been", "will",
    "for", "are", "was", "and", "but", "not", "what", "how", "when",
    "where", "why", "your", "task", "fix", "add", "update", "remove",
    "implement", "build", "create", "delete", "change", "improve",
    "using", "file", "files", "code", "module", "function", "class",
    "run", "test", "check", "read", "write", "edit", "path", "dir",
    "project", "system", "error", "bug", "issue", "problem", "call",
    "use", "get", "set", "new", "name", "type", "value", "data",
    "result", "status", "output", "input", "return", "param", "args",
}


def extract_keywords(filepath: str) -> list[str]:
    """
    Extract meaningful keywords from the file path for LEARNED.md search.
    Looks at:
    1. Path components (e.g. "engine/auth.py" → "auth")
    2. Filename stems (e.g. "skill_execution.py" → "execution", "skill")
    3. Parent directory (e.g. "skills/core/workflow" → "workflow")
    """
    parts = filepath.replace("\\", "/").split("/")
    keywords = []

    # Parent directory is often the most meaningful (e.g. "workflow", "memory")
    if len(parts) >= 2:
        parent = parts[-2]
        stem = Path(parent).stem.lower()
        if stem not in STOPWORDS and len(stem) > 2:
            keywords.append(stem)

    # Filename stem (e.g. "user_decisions" → "decisions", "user")
    filename = parts[-1]
    stem = Path(filename).stem.lower()
    for word in re.findall(r"[a-z_]+", stem):
        if word not in STOPWORDS and len(word) > 2:
            keywords.append(word)

    return list(dict.fromkeys(keywords))  # dedupe, preserve order


def search_learned(keywords: list[str], max_entries: int = 3) -> list[dict]:
    """
    Search LEARNED.md for entries matching any keyword.
    Returns list of matching entries: {date, symptom, root_cause, fix, tags}
    """
    if not LEARNED_FILE.exists():
        return []
    if not keywords:
        return []

    content = LEARNED_FILE.read_text(errors="ignore")
    entries = []
    current = {}

    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("## ["):
            # Save previous entry if it has content
            if current and any(k in " ".join(current.values()).lower() for k in keywords):
                entries.append(current)
            current = {"date": stripped[4:14], "full": stripped}
        elif stripped.startswith("- **"):
            key, _, val = stripped[4:].partition("**")
            key = key.strip().rstrip(":").lower()
            if val.strip():
                current[key] = val.strip()
        elif current:
            current["full"] += "\n" + stripped

        if len(entries) >= max_entries:
            break

    # Don't forget the last entry
    if current and any(k in " ".join(current.values()).lower() for k in keywords):
        entries.append(current)

    return entries


def check_file_for_learned(filepath: str) -> list[dict]:
    """
    Main entry point. Given a file path being modified,
    search LEARNED.md for relevant bugs and return structured warning dicts.
    """
    keywords = extract_keywords(filepath)
    if not keywords:
        return []

    entries = search_learned(keywords, max_entries=2)
    warnings = []

    for entry in entries:
        date = entry.get("date", "?")
        symptom = entry.get("symptom", entry.get("full", ""))[:120]
        fix = entry.get("fix", entry.get("root_cause", ""))[:200]
        tags = entry.get("tags", "")
        root = entry.get("root_cause", "")[:200]
        warnings.append({
            "date": date,
            "filepath": filepath,
            "keywords": keywords,
            "symptom": symptom,
            "fix": fix,
            "root_cause": root,
            "tags": tags,
            "text": (
                f"⚠️  [LEARNED {date}] Related bug — {symptom}\n"
                f"    Fix: {fix}\n"
                f"    Tags: {tags}"
            ),
        })

    return warnings


def _write_recall_cache(warnings: list[dict]):
    """Write warnings to .active_recall.json for session context injection."""
    if not warnings:
        # Clear stale cache if no warnings
        if RECALL_CACHE.exists():
            RECALL_CACHE.unlink()
        return

    # Merge with existing recent warnings (keep last 10 to avoid bloat)
    existing = []
    if RECALL_CACHE.exists():
        try:
            existing = json.loads(RECALL_CACHE.read_text())
        except Exception:
            pass

    # Prepend new warnings, dedupe by (date + symptom), cap at 10
    seen = {(w.get("date"), w.get("symptom")) for w in existing}
    merged = []
    for w in warnings:
        key = (w.get("date"), w.get("symptom"))
        if key not in seen:
            merged.append(w)
            seen.add(key)
    merged.extend(existing)
    merged = merged[:10]

    RECALL_CACHE.write_text(json.dumps(merged, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    # Called with: active-recall.py "filepath"
    if len(sys.argv) < 2:
        sys.exit(0)

    filepath = sys.argv[1]
    warnings = check_file_for_learned(filepath)

    # stderr: visible in transcript immediately
    for w in warnings:
        print(w["text"], file=sys.stderr)

    # Active recall cache: injected into next skill context
    _write_recall_cache(warnings)

    sys.exit(0)
