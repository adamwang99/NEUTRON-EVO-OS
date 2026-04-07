#!/usr/bin/env python3
"""
NEUTRON EVO OS — Lightweight GC for session-start hook
Handles ONLY count-based cleanup (archived/ hard cap) that bash can't do.
Time-based cleanup already handled by session-start.sh find command.
Safe to run on every session start — O(1) per session after cap reached.
"""
from __future__ import annotations

import os
import sys
import tarfile
from pathlib import Path
from datetime import datetime, timedelta

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
ARCHIVED_DIR = MEMORY_DIR / "archived"
PENDING_DIR = MEMORY_DIR / "pending"

# Hard cap: compress oldest files into tarballs when over this threshold.
# Files with timestamps older than COMPRESS_AFTER_DAYS days are compressed.
MAX_ARCHIVED = 100           # hard cap: keep newest N files uncompressed
COMPRESS_AFTER_DAYS = 3      # compress files older than this
MAX_PENDING_AGE_DAYS = 7


def _compress_group(date_prefix: str, files: list, tar_path: Path) -> int:
    """Compress a group of files into a .tar.gz and remove originals. Returns count."""
    try:
        with tarfile.open(str(tar_path), "w:gz") as tar:
            for f in files:
                tar.add(str(f), arcname=f.name)
        for f in files:
            f.unlink()
        return len(files)
    except Exception:
        return 0


def main():
    deleted = 0
    compressed = 0

    if not ARCHIVED_DIR.exists():
        return

    # ── 1. Count-based cap + compression of old files ───────────────────────
    now = datetime.now()
    cutoff = now - timedelta(days=COMPRESS_AFTER_DAYS)

    files = sorted(
        [f for f in ARCHIVED_DIR.iterdir() if f.is_file() and f.suffix != ".tar.gz"],
        key=lambda f: f.stat().st_mtime,
    )

    # Group files older than cutoff by date prefix
    old_by_date = {}
    for f in files:
        stem = f.stem
        if len(stem) >= 10:
            try:
                file_date = datetime.strptime(stem[:10], "%Y-%m-%d")
                if file_date < cutoff:
                    date_prefix = stem[:10]
                    old_by_date.setdefault(date_prefix, []).append(f)
            except ValueError:
                pass

    # Compress old files grouped by date
    for date_prefix, group in sorted(old_by_date.items()):
        tar_name = f"{date_prefix}_session_archive.tar.gz"
        tar_path = ARCHIVED_DIR / tar_name
        if tar_path.exists():
            # Already compressed — delete individual files
            for f in group:
                try:
                    f.unlink()
                    deleted += 1
                except Exception:
                    pass
        else:
            n = _compress_group(date_prefix, sorted(group), tar_path)
            compressed += n

    # Delete oldest uncompressed files if still over MAX_ARCHIVED
    remaining = sorted(
        [f for f in ARCHIVED_DIR.iterdir()
         if f.is_file() and f.suffix not in (".tar.gz", ".lock")],
        key=lambda f: f.stat().st_mtime,
    )
    while len(remaining) > MAX_ARCHIVED:
        oldest = remaining.pop(0)
        try:
            oldest.unlink()
            deleted += 1
        except Exception:
            pass

    # ── 2. Prune old pending entries (auto-expire after 7 days) ───────────
    if PENDING_DIR.exists():
        pending_file = PENDING_DIR / "LEARNED_pending.md"
        if pending_file.exists():
            pending_cutoff = datetime.now() - timedelta(days=MAX_PENDING_AGE_DAYS)
            content = pending_file.read_text()
            lines = content.splitlines()
            kept = []
            for line in lines:
                if line.startswith("## ["):
                    try:
                        m = datetime.strptime(line[4:14], "%Y-%m-%d")
                        if m >= pending_cutoff:
                            kept.append(line)
                    except (ValueError, IndexError):
                        kept.append(line)  # malformed line — keep it
                else:
                    kept.append(line)
            if len(kept) < len(lines):
                pending_file.write_text("\n".join(kept))

    # ── 3. Prune empty directories in archived/ ─────────────────────────────
    for subdir in ARCHIVED_DIR.iterdir():
        if subdir.is_dir() and not any(subdir.iterdir()):
            try:
                subdir.rmdir()
            except Exception:
                pass

    msg_parts = []
    if deleted:
        msg_parts.append(f"deleted {deleted} files")
    if compressed:
        msg_parts.append(f"compressed {compressed} files into tar.gz")
    if msg_parts:
        print(f"🗑️ GC: {', '.join(msg_parts)} (cap={MAX_ARCHIVED}, compress after {COMPRESS_AFTER_DAYS}d)")

if __name__ == "__main__":
    main()
