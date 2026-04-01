"""
NEUTRON-EVO-OS: Skill Execution Pipeline
validate → execute → log → update CI
"""
from __future__ import annotations

import importlib
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from filelock import FileLock

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"

# Ensure repo root is in sys.path so skill modules can be imported as packages.
_REPO_ROOT = str(NEUTRON_ROOT)
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)


def run(skill_name: str, task: str, context: dict = None) -> dict:
    """
    Full execution pipeline for a skill.

    1. Validate: skill exists, has logic, inputs valid
    2. Execute: call skill's logic.<name>(task, context)
    3. Log: append result to memory/YYYY-MM-DD.md
    4. Update CI: apply delta from execution result

    Returns: {status, output, ci_delta, skill, duration_ms}
    """
    from engine.expert_skill_router import get_ledger_entry, update_ci
    from engine.skill_registry import get_skill, has_logic

    start = time.time()
    context = context or {}

    # --- Validation: skill exists ---
    skill = get_skill(skill_name)
    if not skill:
        return {"status": "error", "output": f"Skill '{skill_name}' not found", "ci_delta": 0}

    # --- Validation: confidence gate ---
    # If caller passed routing confidence, gate on it.
    # confidence < 0.4 means routing is uncertain — warn but allow.
    routing_confidence = context.get("_routing_confidence", 1.0)
    if routing_confidence < 0.4:
        context["_low_confidence"] = True  # flag for caller awareness

    # --- Validation: CI gate ---
    ledger = get_ledger_entry(skill_name)
    if ledger["CI"] < 30:
        return {
            "status": "blocked",
            "output": f"Skill '{skill_name}' CI={ledger['CI']} < 30 — requires human review",
            "ci_delta": 0,
        }

    # --- Validation: run validation module if real content exists ---
    validation_error = _run_validation(skill_name, {"task": task, "context": context})
    if validation_error:
        return {
            "status": "validation_failed",
            "output": validation_error,
            "ci_delta": -5,
            "skill": skill_name,
        }

    # --- Execute: call logic module ---
    if not has_logic(skill_name):
        return {
            "status": "not_implemented",
            "output": f"Skill '{skill_name}' logic module is a stub. Read SKILL.md for execution guidance.",
            "skill": skill_name,
            "ci_delta": 0,
        }

    result = _execute_logic(skill_name, task, context)

    # --- Log: append to daily log ---
    _write_execution_log(skill_name, task, result)

    # --- CI update ---
    ci_delta = result.get("ci_delta", 0)
    if ci_delta != 0:
        update_ci(skill_name, ci_delta)

    duration_ms = int((time.time() - start) * 1000)

    # Pass through extra fields from skill result (not just the fixed 5)
    ret = {
        "status": result.get("status", "ok"),
        "output": result.get("output", ""),
        "ci_delta": ci_delta,
        "skill": skill_name,
        "duration_ms": duration_ms,
    }
    # Merge extra keys (questions_remaining, complexity, can_ship, etc.)
    for k, v in result.items():
        if k not in ret:
            ret[k] = v
    return ret


def _run_validation(skill_name: str, inputs: dict) -> Optional[str]:
    """
    Run skill's validation module if it has real content.
    Returns error string or None.
    """
    from engine.skill_registry import get_skill

    skill = get_skill(skill_name)
    if not skill or not skill["has_validation"]:
        return None

    try:
        mod = importlib.import_module(f"skills.core.{skill_name}.validation")
    except ImportError:
        return None

    validate_fn = getattr(mod, f"validate_{skill_name}", None)
    if validate_fn is None:
        return None

    try:
        valid = validate_fn(inputs)
        if valid is True or valid is None:
            return None
        return str(valid)
    except Exception as e:
        return f"Validation error: {e}"


def _execute_logic(skill_name: str, task: str, context: dict) -> dict:
    """
    Call the skill's run_<skill_name>(task, context) function via importlib.
    Supports both core skills (skills.core.<name>) and learned skills
    (skills.learned.<slug>).
    """
    # Determine which package to import from
    if skill_name == "learned":
        # Special case: learned skill invocation
        # skill_name in context is the specific learned skill slug/name
        learned_skill = context.get("skill", context.get("skill_name", "")) if context else ""
        if not learned_skill:
            return {"status": "error", "output": "No learned skill name provided in context", "ci_delta": 0}
        mod_path = f"skills.learned.{learned_skill}.logic"
        fn_prefix = f"run_learned_{learned_skill}"
    else:
        # Check registry: is this a learned skill with a custom slug?
        try:
            from engine.skill_registry import get_skill
            skill = get_skill(skill_name)
            if skill and skill.get("type") == "learned":
                slug = skill.get("slug", skill_name)
                mod_path = f"skills.learned.{slug}.logic"
                fn_prefix = f"run_learned_{slug}"
            else:
                mod_path = f"skills.core.{skill_name}.logic"
                fn_prefix = f"run_{skill_name}"
        except Exception:
            mod_path = f"skills.core.{skill_name}.logic"
            fn_prefix = f"run_{skill_name}"

    try:
        mod = importlib.import_module(mod_path)
    except ImportError as e:
        return {"status": "import_error", "output": f"{mod_path}: {e}", "ci_delta": 0}

    run_fn = getattr(mod, fn_prefix, None)
    if run_fn is None:
        return {"status": "no_run_function", "output": f"{fn_prefix}() not found in {mod_path}", "ci_delta": 0}

    try:
        return run_fn(task, context)
    except Exception as e:
        return {"status": "execution_error", "output": str(e), "ci_delta": -10}


def _write_execution_log(skill_name: str, task: str, result: dict):
    """Append skill execution to today's daily log (atomic write via filelock)."""
    MEMORY_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = MEMORY_DIR / f"{today}.md"
    lock_path = MEMORY_DIR / f"{today}.lock"

    timestamp = datetime.now().strftime("%H:%M")
    ci_delta = result.get("ci_delta", 0)
    status = result.get("status", "ok")
    output = str(result.get("output", ""))[:120]

    entry = (
        f"\n## [{timestamp}] — Skill: {skill_name} | Task: {task[:60]}\n"
        f"- Action: execute_skill({skill_name})\n"
        f"- Outcome: {status}\n"
        f"- CI delta: {ci_delta:+.0f}\n"
        f"- Notes: {output}\n"
    )

    # Atomic write: hold lock for the full read+write to prevent concurrent corruption
    with FileLock(str(lock_path), timeout=10):
        if log_path.exists():
            try:
                existing = log_path.read_text(errors="replace")
            except Exception:
                existing = ""  # Corrupted file — start fresh
            log_path.write_text(existing + entry)
        else:
            log_path.write_text(f"# {today}\n{entry}\n")
