#!/usr/bin/env python3
"""
NEUTRON EVO OS — Lightweight GC for session-start hook
Handles ONLY count-based cleanup (archived/ hard cap) that bash find can't do.
Time-based cleanup already handled by session-start.sh find command.
Safe to run on every session start — O(1) per session after cap reached.
"""
from __future__ import annotations

import os, sys
from pathlib import Path
from datetime import datetime, timedelta

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
ARCHIVED_DIR = MEMORY_DIR / "archived"
PENDING_DIR = MEMORY_DIR / "pending"

MAX_ARCHIVED = 500   # hard cap: delete oldest beyond this
MAX_PENDING_AGE_DAYS = 7

def main():
    deleted = 0

    # 1. Count-based cap on archived/ (bash find can't do this efficiently)
    if ARCHIVED_DIR.exists():
        files = sorted(ARCHIVED_DIR.iterdir(), key=lambda f: f.stat().st_mtime)
        while len(files) > MAX_ARCHIVED:
            oldest = files.pop(0)
            try:
                oldest.unlink()
                deleted += 1
            except Exception:
                pass

    # 2. Prune old pending entries (auto-expire after 7 days)
    if PENDING_DIR.exists():
        pending_file = PENDING_DIR / "LEARNED_pending.md"
        if pending_file.exists():
            cutoff = datetime.now() - timedelta(days=MAX_PENDING_AGE_DAYS)
            content = pending_file.read_text()
            lines = content.splitlines()
            kept = []
            for line in lines:
                if line.startswith("## ["):
                    m = datetime.strptime(line[4:14], "%Y-%m-%d")
                    if m < cutoff:
                        continue  # skip expired
                kept.append(line)
            if len(kept) < len(lines):
                pending_file.write_text("\n".join(kept))

    if deleted:
        print(f"🗑️ GC: cleaned {deleted} archived files (count cap {MAX_ARCHIVED})")

if __name__ == "__main__":
    main()