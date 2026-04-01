"""
Learned Skills — Validation Module
validate_learned(inputs) → True or error string
"""
from __future__ import annotations
from typing import Union

VALID_ACTIONS = {"distill", "register", "list", "invoke", "promote", "stale"}


def validate_learned(inputs: dict) -> Union[bool, str]:
    ctx = inputs.get("context", {})
    action = ctx.get("action", "list")

    if action not in VALID_ACTIONS:
        return f"Invalid action: '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"

    if action == "register":
        for field in ["name", "pattern", "when_to_apply"]:
            if not ctx.get(field):
                return f"register action requires '{field}' in context"

    if action == "invoke" and not ctx.get("skill_name") and not inputs.get("task", "").strip():
        return "invoke action requires 'skill_name' in context"

    task = inputs.get("task", "")
    if len(task) > 500:
        return f"Task too long ({len(task)} chars). Max 500."

    return True
