"""
Checkpoint Skill — Validation Module
validate_checkpoint(inputs) → True or error string
"""
from __future__ import annotations
from typing import Union

VALID_ACTIONS = {"write", "read", "handoff"}
VALID_CONFIDENCE = {"low", "medium", "high"}


def validate_checkpoint(inputs: dict) -> Union[bool, str]:
    """
    Validate checkpoint skill inputs before execution.
    Returns True if valid, error string if invalid.
    """
    ctx = inputs.get("context", {})
    action = ctx.get("action", "write")

    if action not in VALID_ACTIONS:
        return f"Invalid action: '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"

    confidence = ctx.get("confidence", "medium")
    if confidence not in VALID_CONFIDENCE:
        return f"Invalid confidence: '{confidence}'. Must be: {', '.join(sorted(VALID_CONFIDENCE))}"

    task = inputs.get("task", "")
    if len(task) > 500:
        return f"Task too long ({len(task)} chars). Max 500."

    return True
