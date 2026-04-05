"""
NEUTRON-EVO-OS: Atomic Write Utilities
Shared primitives for crash-safe file writes.
"""
from __future__ import annotations

import os
import tempfile
from pathlib import Path


def atomic_write(path: Path, content: str) -> None:
    """
    Write content to path atomically: write to temp file → fsync → rename.

    This prevents partial-write corruption on crash:
    - Crash during write → original file is untouched (replaced only by complete temp)
    - Never leaves a half-written file

    Thread-safe when combined with filelock on the caller side.

    Args:
        path: Target file path (absolute or relative)
        content: String content to write
    """
    path = Path(path)
    # Ensure parent directory exists before creating temp file
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = None
    tmp_name = None
    try:
        tmp = tempfile.NamedTemporaryFile(
            mode="w",
            dir=str(path.parent),
            delete=False,
            encoding="utf-8",
        )
        tmp_name = tmp.name  # Capture name before closing
        tmp.write(content)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp.close()
        tmp = None
        os.replace(tmp_name, str(path))
    except Exception:
        if tmp is not None:
            try:
                tmp.close()
            except Exception:
                pass
        if tmp_name is not None:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            except Exception:
                pass
        raise
