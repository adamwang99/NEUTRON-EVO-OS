"""UI Library Skill — Validation Module."""
from __future__ import annotations
from typing import Union


def validate_ui_library(inputs: dict) -> Union[bool, str]:
    """Validate inputs for ui_library skill."""
    task = inputs.get("task", "")
    context = inputs.get("context", {}) or {}

    # No strict validation needed — skill returns needs_info if params missing
    if not task and not context.get("tech_stack"):
        return True  # Let logic handle it with needs_info response

    return True
