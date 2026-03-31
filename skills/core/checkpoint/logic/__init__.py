"""
Checkpoint Skill — Logic Module
run_checkpoint(task, context) → {status, output, ci_delta}

Actions (passed via context["action"]):
  - write  : write a new checkpoint entry
  - read   : read the latest checkpoint
  - handoff: write full session handoff (transcript + checkpoint)

Inputs via context dict:
  - task       : task description
  - notes      : additional notes
  - confidence : low | medium | high
"""
from __future__ import annotations

import os
import subprocess
from pathlib import Path

# Use NEUTRON_ROOT env var (set by install-global.sh), fallback to repo root
# Levels: logic/__init__.py → checkpoint/ → core/ → skills/ → repo root
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent.parent)
))
CHECKPOINT_CLI = _NEUTRON_ROOT / "engine" / "checkpoint_cli.py"


def run_checkpoint(task: str, context: dict = None) -> dict:
    context = context or {}
    action = context.get("action", "write")

    if action == "read":
        return _read_checkpoint()
    elif action == "handoff":
        return _handoff_checkpoint(context)
    else:
        return _write_checkpoint(context)


def _subprocess_env() -> dict:
    """Build env dict with NEUTRON_ROOT set for subprocess calls."""
    env = dict(os.environ)
    env["NEUTRON_ROOT"] = str(_NEUTRON_ROOT)
    return env


def _write_checkpoint(context: dict) -> dict:
    result = subprocess.run(
        ["python3", str(CHECKPOINT_CLI),
         "--task", context.get("task", "Untitled"),
         "--notes", context.get("notes", ""),
         "--confidence", context.get("confidence", "medium")],
        capture_output=True, text=True, timeout=30, env=_subprocess_env(),
    )
    if result.returncode == 0:
        return {"status": "ok", "output": result.stdout.strip(), "ci_delta": 5}
    return {"status": "error", "output": result.stderr.strip() or "Write failed", "ci_delta": -5}


def _read_checkpoint() -> dict:
    result = subprocess.run(
        ["python3", str(CHECKPOINT_CLI), "--read"],
        capture_output=True, text=True, timeout=15, env=_subprocess_env(),
    )
    if result.returncode == 0:
        return {"status": "ok", "output": result.stdout.strip(), "ci_delta": 0}
    return {"status": "error", "output": result.stderr.strip() or "No checkpoint", "ci_delta": 0}


def _handoff_checkpoint(context: dict) -> dict:
    result = subprocess.run(
        ["python3", str(CHECKPOINT_CLI),
         "--handoff",
         "--task", context.get("task", "Handoff"),
         "--notes", context.get("notes", "Context handoff")],
        capture_output=True, text=True, timeout=30, env=_subprocess_env(),
    )
    if result.returncode == 0:
        return {"status": "ok", "output": result.stdout.strip(), "ci_delta": 3}
    return {"status": "error", "output": result.stderr.strip() or "Handoff failed", "ci_delta": -5}
