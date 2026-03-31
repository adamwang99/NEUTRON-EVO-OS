"""
Engine Skill — Validation Module
validate_engine(inputs) → True or error string
"""
from __future__ import annotations
from typing import Union

VALID_ACTIONS = {"audit", "route", "observer_start", "observer_stop"}


def validate_engine(inputs: dict) -> Union[bool, str]:
    ctx = inputs.get("context", {})
    action = ctx.get("action", "route")
    if action not in VALID_ACTIONS:
        return f"Invalid action: '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"

    task = inputs.get("task", "")
    if len(task) > 500:
        return f"Task too long ({len(task)} chars). Max 500."

    return True
