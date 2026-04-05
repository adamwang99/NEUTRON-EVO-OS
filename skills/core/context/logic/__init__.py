"""
Context Skill — Logic Module
run_context(task, context) → {status, output, missing_files, load_order_ok, ci_delta}

Validates that P0/P1 context files are present and not corrupted.
P0 files: SOUL.md, MANIFESTO.md (always required)
P1 files: USER.md, GOVERNANCE.md, RULES.md (always required)
P2 file:  PERFORMANCE_LEDGER.md (required for CI tracking)
"""
from __future__ import annotations

import os
from pathlib import Path

# Levels: logic/__init__.py → context/ → core/ → skills/ → repo root
NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent)
))

CONTEXT_ORDER = [
    ("P0", "SOUL.md"),
    ("P0", "MANIFESTO.md"),
    ("P1", "USER.md"),
    ("P1", "GOVERNANCE.md"),
    ("P1", "RULES.md"),
    ("P2", "PERFORMANCE_LEDGER.md"),
]


def run_context(task: str, context: dict = None) -> dict:
    context = context or {}
    missing = []
    present = []

    for priority, filename in CONTEXT_ORDER:
        path = NEUTRON_ROOT / filename
        if not path.exists():
            missing.append(f"[{priority}] {filename}")
        elif path.is_file() and path.stat().st_size < 10:
            missing.append(f"[{priority}] {filename} (corrupted: too small)")
        else:
            present.append(f"[{priority}] {filename}")

    if missing:
        return {
            "status": "degraded",
            "output": f"Missing/corrupted: {', '.join(missing)}",
            "missing_files": missing,
            "load_order_ok": False,
            "ci_delta": -5,
        }
    return {
        "status": "ok",
        "output": f"All {len(present)}/{len(CONTEXT_ORDER)} context files present and valid",
        "missing_files": [],
        "load_order_ok": True,
        "ci_delta": 3,
    }
