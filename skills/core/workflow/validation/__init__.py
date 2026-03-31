"""
Workflow Skill — Validation Module
validate_workflow(inputs) → True or error string
"""
from __future__ import annotations
from typing import Union

VALID_STEPS = {"explore", "discovery", "spec", "build", "verify", "acceptance", "ship", "auto"}


def validate_workflow(inputs: dict) -> Union[bool, str]:
    ctx = inputs.get("context", {})
    step = ctx.get("step", "explore")

    if step not in VALID_STEPS:
        return f"Invalid step: '{step}'. Must be one of: {', '.join(sorted(VALID_STEPS))}"

    if step == "auto":
        mode = ctx.get("mode", "full")
        valid_modes = {"full", "spec_only", "discovery_only", "acceptance_only", "spec_and_acceptance", "disable"}
        if mode not in valid_modes:
            return f"Invalid auto mode: '{mode}'. Must be one of: {', '.join(sorted(valid_modes))}"

    if step == "discovery":
        task = inputs.get("task", "")
        if len(task.strip()) < 5:
            return "Discovery requires a project idea or prompt"

    if step == "ship":
        rating = ctx.get("rating")
        if rating is not None:
            try:
                r = int(rating)
                if not (1 <= r <= 5):
                    return "Rating must be 1-5"
            except (ValueError, TypeError):
                return "Rating must be an integer 1-5"

    task = inputs.get("task", "")
    if len(task) > 500:
        return f"Task too long ({len(task)} chars). Max 500."

    return True
