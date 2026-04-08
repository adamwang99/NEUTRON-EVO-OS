#!/usr/bin/env python3
"""
check-learned-entry.py — pre-commit hook
For "fix:" commits, verifies the bug fix has a LEARNED.md entry with matching keyword.
Checks: commit message starts with "fix:" AND LEARNED.md has an entry matching the bug.
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

def get_commit_msg() -> str:
    """Get commit message from git or stdin."""
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


def extract_bug_keywords(msg: str) -> list[str]:
    """
    Extract bug keywords from commit message.
    'fix: add LEARNED.md entry for <bug description>'
    → extracts '<bug description>' words
    """
    # Match "fix: <anything>" — extract everything after the prefix
    m = re.match(r"^fix:\s*(.+)", msg.strip(), re.IGNORECASE)
    if not m:
        return []
    raw = m.group(1)
    # Remove common commit boilerplate
    for skip in ["add LEARNED.md entry for", "record audit bug", "fix: "]:
        raw = re.sub(rf"\b{re.escape(skip)}\b", "", raw, flags=re.IGNORECASE)
    # Extract 3+ char words
    words = re.findall(r"[a-z_]{3,}", raw.lower())
    # Filter stopwords
    stop = {"bug", "fix", "add", "for", "entry", "learned", "memory", "module", "file"}
    return [w for w in words if w not in stop]


def search_learned_for_keywords(keywords: list[str], learned_path: Path) -> bool:
    """
    Search LEARNED.md for at least one entry whose content matches ANY keyword.
    Returns True if a match is found.
    """
    if not learned_path.exists():
        return False
    content = learned_path.read_text(errors="ignore").lower()
    matched = [kw for kw in keywords if kw in content]
    return len(matched) >= 1


def check() -> bool:
    """Return True if check passes (commit is valid)."""
    msg = get_commit_msg()

    # Only check "fix:" commits
    if not re.match(r"^fix:", msg.strip()):
        return True  # skip non-fix commits

    keywords = extract_bug_keywords(msg)
    learned = Path("memory/LEARNED.md")

    if not learned.exists() or "## [" not in learned.read_text():
        print("ERROR: 'fix:' commit but memory/LEARNED.md is empty or missing.")
        print("  → Every bug fix MUST have a LEARNED.md entry.")
        sys.exit(1)

    # Strict check: keywords from commit message must appear in LEARNED.md
    if keywords:
        if not search_learned_for_keywords(keywords, learned):
            print(f"ERROR: 'fix:' commit but no LEARNED.md entry matches the fix.")
            print(f"  → Keywords checked: {keywords}")
            print("  → Every bug fix MUST be recorded in memory/LEARNED.md")
            print("  → Add entry and run: git add memory/LEARNED.md && git commit --amend")
            sys.exit(1)

    return True


if __name__ == "__main__":
    sys.exit(0 if check() else 1)
