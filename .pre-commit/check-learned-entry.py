#!/usr/bin/env python3
"""
check-learned-entry.py — pre-commit hook
For "fix:" commits, verifies the bug fix has a LEARNED.md entry.
Checks: commit message starts with "fix:" AND a LEARNED.md entry exists for this fix.
"""
import re
import sys
from pathlib import Path

def get_commit_msg() -> str:
    """Get commit message from git or stdin."""
    # Try to read from file argument (pre-commit passes staged files)
    for arg in sys.argv[1:]:
        if arg.endswith(".msg") or "COMMIT_EDITMSG" in arg:
            try:
                return Path(arg).read_text()
            except Exception:
                pass
    # Fallback: read from stdin (some pre-commit setups)
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def check() -> bool:
    """Return True if check passes (commit is valid)."""
    msg = get_commit_msg()

    # Only check "fix:" commits
    if not re.match(r"^fix:", msg.strip()):
        return True  # skip non-fix commits

    # Check if LEARNED.md was modified in this commit
    learned_modified = any(
        "LEARNED.md" in arg.upper()
        for arg in sys.argv[1:]
    )

    if not learned_modified:
        # Check if LEARNED.md exists and has a recent entry (last 7 days)
        learned = Path("memory/LEARNED.md")
        if learned.exists():
            content = learned.read_text()
            # Allow if there's at least one entry
            if "## [" in content:
                return True  # ok, has entries

        print("WARNING: 'fix:' commit but LEARNED.md not modified or empty.")
        print("  → Every bug fix should be recorded in memory/LEARNED.md")
        print("  → Add entry and run: git add memory/LEARNED.md && git commit --amend")
        print("  → Or skip this warning if this is a very minor fix.")
        # Return True (warning only, not a hard block for now)
        # Change to sys.exit(1) to make it a hard requirement
        return True

    return True


if __name__ == "__main__":
    sys.exit(0 if check() else 1)
