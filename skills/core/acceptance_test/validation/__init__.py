"""
Acceptance Test Skill — Validation Module
validate_acceptance_test(inputs) → True or error string
"""
from __future__ import annotations
from typing import Union

VALID_ACTIONS = {"prepare", "pass", "fail", "status"}


def validate_acceptance_test(inputs: dict) -> Union[bool, str]:
    ctx = inputs.get("context", {})
    action = ctx.get("action", "prepare")

    if action not in VALID_ACTIONS:
        return f"Invalid action: '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"

    if action == "pass":
        # User confirming acceptance — no further validation needed
        pass

    if action == "fail":
        notes = ctx.get("notes", "")
        if not notes or len(notes.strip()) < 3:
            return "fail action requires 'notes' describing what failed"

    task = inputs.get("task", "")
    if len(task) > 500:
        return f"Task too long ({len(task)} chars). Max 500."

    return True
