"""
Discovery Skill — Validation Module
validate_discovery(inputs) → True or error string
"""
from __future__ import annotations
from typing import Union

VALID_ACTIONS = {"start", "record", "status"}


def validate_discovery(inputs: dict) -> Union[bool, str]:
    ctx = inputs.get("context", {})
    action = ctx.get("action", "start")

    if action not in VALID_ACTIONS:
        return f"Invalid action: '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"

    task = inputs.get("task", "")
    if action == "start":
        if len(task.strip()) < 5:
            return "Task/prompt too short. Provide your project idea or spec to begin discovery."

    if action == "record":
        answers = ctx.get("answers", {})
        if not answers:
            return "record action requires 'answers' dict in context"

    if len(task) > 2000:
        return f"Task too long ({len(task)} chars). Max 2000."

    return True
