"""NEUTRON-EVO-OS Engine — Core Python components."""
from __future__ import annotations

__version__ = "4.4.0"
__all__ = [
    "NEUTRON_ROOT",
    "MEMORY_DIR",
    "LEDGER_PATH",
    "expert_skill_router",
    "dream_engine",
    "smart_observer",
    "checkpoint_cli",
    "auto_confirm",
    "skill_execution",
    "rating",
    "user_decisions",
    "learned_skill_builder",
    "context_snapshot",
    "regression_guard",
]

from pathlib import Path

NEUTRON_ROOT: Path = Path(__file__).parent.parent
MEMORY_DIR: Path = NEUTRON_ROOT / "memory"
LEDGER_PATH: Path = NEUTRON_ROOT / "PERFORMANCE_LEDGER.md"

from . import expert_skill_router
from . import dream_engine
from . import smart_observer
from . import checkpoint_cli
from . import auto_confirm
from . import skill_execution
from . import rating
from . import user_decisions
from . import learned_skill_builder
from . import context_snapshot

# ── Session End Hook (atexit) ──────────────────────────────────────────────────
# Triggers session-end.sh on Python process exit (normal or crash).
# This is safe to call multiple times — shell script is idempotent.
import atexit, os, subprocess

_SESSION_END_SCRIPT = NEUTRON_ROOT / "hooks" / "session-end.sh"


def _run_session_end():
    if not _SESSION_END_SCRIPT.exists():
        return
    try:
        # Use subprocess.DEVNULL to prevent blocking on broken pipe
        subprocess.run(
            ["bash", str(_SESSION_END_SCRIPT)],
            cwd=str(NEUTRON_ROOT),
            env={**os.environ, "NEUTRON_ROOT": str(NEUTRON_ROOT)},
            timeout=30,
            capture_output=True,
        )
    except Exception:
        pass  # Best-effort: never block exit


atexit.register(_run_session_end)
