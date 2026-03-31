"""
Engine Skill — Logic Module
run_engine(task, context) → {status, output, ci_delta}

Actions (via context["action"]):
  - audit          : full CI health check (delegates to expert_skill_router.audit)
  - route          : route a task string  (delegates to expert_skill_router.route_task)
  - observer_start : start SilentObserver with Dream Cycle callback
  - observer_stop   : stop SilentObserver

CI: audit/route = +2, observer start = +2, failure = -3
Non-circular: only calls engine submodules, NEVER calls skill_execution.run().
"""
from __future__ import annotations

import os
from pathlib import Path

# Levels: logic/__init__.py → engine/ → core/ → skills/ → repo root
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent.parent)
))


def run_engine(task: str, context: dict = None) -> dict:
    context = context or {}
    action = context.get("action", "route")

    if action == "audit":
        return _do_audit()
    elif action == "route":
        return _do_route(task, context)
    elif action == "observer_start":
        return _observer_start(context)
    elif action == "observer_stop":
        return _observer_stop()
    else:
        return {"status": "error", "output": f"Unknown action: '{action}'", "ci_delta": 0}


def _do_audit() -> dict:
    from engine.expert_skill_router import audit
    result = audit()
    return {"status": "ok", "output": result, "ci_delta": 2}


def _do_route(task: str, context: dict) -> dict:
    from engine.expert_skill_router import route_task
    result = route_task(task, context)
    return {"status": "ok", "output": result, "ci_delta": 2}


def _observer_start(context: dict) -> dict:
    from engine.smart_observer import SilentObserver
    from engine.dream_engine import dream_cycle

    root = context.get("root", str(_NEUTRON_ROOT))
    debounce = context.get("debounce_seconds", 30)

    try:
        SilentObserver.start(root, dream_cycle, debounce_seconds=debounce)
        return {"status": "started", "output": f"Observer running on {root}", "ci_delta": 2}
    except Exception as e:
        return {"status": "error", "output": f"Observer start failed: {e}", "ci_delta": -3}


def _observer_stop() -> dict:
    from engine.smart_observer import SilentObserver
    try:
        SilentObserver.stop()
        return {"status": "stopped", "output": "Observer stopped", "ci_delta": 0}
    except Exception as e:
        return {"status": "error", "output": f"Observer stop failed: {e}", "ci_delta": 0}
