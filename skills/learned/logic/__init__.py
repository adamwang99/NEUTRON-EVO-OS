"""
Learned Skills — Logic Module
Delegates all actions to engine/learned_skill_builder.py.
run_learned(task, context) → {status, output, ci_delta}
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent)
))
if str(_NEUTRON_ROOT) not in sys.path:
    sys.path.insert(0, str(_NEUTRON_ROOT))


def run_learned(task: str, context: dict = None) -> dict:
    """
    Learned skills wrapper — delegates to learned_skill_builder.
    Context may include 'skill' (learned skill name) for specific invocation.
    """
    from engine.learned_skill_builder import run_learn
    return run_learn(task, context)
