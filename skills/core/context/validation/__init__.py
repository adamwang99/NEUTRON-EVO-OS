"""
Context Skill — Validation Module
validate_context(inputs) → True or error string
"""
from __future__ import annotations
from typing import Union


def validate_context(inputs: dict) -> Union[bool, str]:
    """
    Validate context skill inputs before execution.
    Returns True if valid, error string if invalid.
    """
    task = inputs.get("task", "")
    if len(task) > 2000:
        return f"Task description too long ({len(task)} chars). Max 2000."
    return True
