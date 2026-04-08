#!/usr/bin/env python3
"""
NEUTRON EVO OS — Active Recall: LEARNED Pattern Matcher

Run by PreToolUse hook before every file Edit/Write.
Greps memory/LEARNED.md for bug patterns relevant to the file being modified.
If patterns found → writes warning to stderr → Claude Code shows it to the user.

This is the ENFORCEMENT MECHANISM for LEARNED.md:
Before every code change, the system asks: "Has this bug happened before?"
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path
from datetime import datetime

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
LEARNED_FILE = MEMORY_DIR / "LEARNED.md"

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


def check_file_for_learned(filepath: str) -> list[str]:
    """
    Main entry point. Given a file path being modified,
    search LEARNED.md for relevant bugs and return warning lines.
    """
    keywords = extract_keywords(filepath)
    if not keywords:
        return []

    entries = search_learned(keywords, max_entries=2)
    warnings = []

    for entry in entries:
        date = entry.get("date", "?")
        symptom = entry.get("symptom", entry.get("full", ""))[:120]
        fix = entry.get("fix", entry.get("root_cause", ""))[:120]
        tags = entry.get("tags", "")

        warnings.append(
            f"⚠️  [LEARNED {date}] Related bug — {symptom}\n"
            f"    Fix: {fix}\n"
            f"    Tags: {tags}"
        )

    return warnings


if __name__ == "__main__":
    # Called with: active-recall.py "filepath"
    if len(sys.argv) < 2:
        sys.exit(0)

    filepath = sys.argv[1]
    warnings = check_file_for_learned(filepath)

    for w in warnings:
        print(w, file=sys.stderr)

    sys.exit(0)
