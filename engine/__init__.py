"""NEUTRON-EVO-OS Engine — Core Python components."""
from __future__ import annotations

__version__ = "4.1.0"
__all__ = [
    "NEUTRON_ROOT",
    "MEMORY_DIR",
    "LEDGER_PATH",
    "expert_skill_router",
    "dream_engine",
    "smart_observer",
    "checkpoint_cli",
]

from pathlib import Path

NEUTRON_ROOT: Path = Path(__file__).parent.parent
MEMORY_DIR: Path = NEUTRON_ROOT / "memory"
LEDGER_PATH: Path = NEUTRON_ROOT / "PERFORMANCE_LEDGER.md"

from . import expert_skill_router
from . import dream_engine
from . import smart_observer
from . import checkpoint_cli
