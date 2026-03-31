"""
Memory Skill — Validation Module
validate_memory(inputs) → True or error string
"""
from __future__ import annotations
from typing import Union

VALID_ACTIONS = {"log", "archive", "search", "dream", "status"}


def validate_memory(inputs: dict) -> Union[bool, str]:
    ctx = inputs.get("context", {})
    action = ctx.get("action", "log")

    if action not in VALID_ACTIONS:
        return f"Invalid action: '{action}'. Must be one of: {', '.join(sorted(VALID_ACTIONS))}"

    if action == "search" and not ctx.get("query", "").strip():
        return "search action requires 'query' in context"

    if action == "archive" and not ctx.get("file_path"):
        return "archive action requires 'file_path' in context"

    task = inputs.get("task", "")
    if len(task) > 500:
        return f"Task too long ({len(task)} chars). Max 500."

    return True
