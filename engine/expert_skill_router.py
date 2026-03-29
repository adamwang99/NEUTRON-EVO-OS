"""
NEUTRON-EVO-OS: Expert Skill Router
Audits PERFORMANCE_LEDGER.md before executing any skill.
Routes tasks to appropriate skills based on CI scores and availability.
"""
import os
import re
from pathlib import Path
from typing import Optional

LEDGER_PATH = Path(__file__).parent.parent / "PERFORMANCE_LEDGER.md"
SKILLS_DIR = Path(__file__).parent.parent / "skills"

# CI thresholds
CI_FULL_TRUST = 70
CI_NORMAL = 40
CI_RESTRICTED = 30
CI_BLOCKED = 30  # below this: block


def get_ledger_entry(skill_name: str) -> dict:
    """
    Retrieve CI score and stats for a skill from the PERFORMANCE_LEDGER.md.
    Returns: {CI: int, tasks_completed: int, last_active: str}
    """
    if not LEDGER_PATH.exists():
        return {"CI": 50, "tasks_completed": 0, "last_active": "-"}

    content = LEDGER_PATH.read_text()

    # Find the skill row (case-insensitive)
    pattern = re.compile(
        rf"^\|\s*{re.escape(skill_name)}\s*\|.*?(\d+).*?\|.*?(\d+).*?\|\s*(.*?)\s*\|",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(content)
    if match:
        return {
            "CI": int(match.group(1)),
            "tasks_completed": int(match.group(2)),
            "last_active": match.group(3).strip(),
        }

    # Skill not in ledger — initialize at neutral CI
    return {"CI": 50, "tasks_completed": 0, "last_active": "-"}


def get_all_skill_entries() -> dict:
    """Return all skill entries from the ledger."""
    entries = {}
    if not LEDGER_PATH.exists():
        return entries

    content = LEDGER_PATH.read_text()
    pattern = re.compile(
        r"^\|\s*(\w+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(.*?)\s*\|",
        re.MULTILINE,
    )
    for match in pattern.finditer(content):
        skill = match.group(1)
        entries[skill] = {
            "CI": int(match.group(2)),
            "tasks_completed": int(match.group(3)),
            "last_active": match.group(4).strip(),
        }
    return entries


def route_task(task: str, context: dict = None) -> dict:
    """
    Route a task to the best matching skill.
    Performs pre-route CI audit.

    Returns: {skill, confidence, reasoning, blocked, block_reason}
    """
    from datetime import datetime

    task_lower = task.lower()
    context = context or {}

    # --- Skill mapping ---
    skill_map = {
        "context": ["context", "load", "inject", "priority", "claude.md", "ide window"],
        "memory": ["memory", "log", "archive", "daily", "remember", "recall"],
        "workflow": ["workflow", "/explore", "/spec", "/build", "/verify", "/ship", "step"],
        "engine": ["engine", "router", "route", "ci", "audit", "observer", "dream"],
    }

    candidates = []
    for skill, keywords in skill_map.items():
        score = 0
        for kw in keywords:
            if kw in task_lower:
                score += 1
        if score > 0:
            entry = get_ledger_entry(skill)
            candidates.append((skill, score, entry["CI"]))

    if not candidates:
        # Default to workflow for unknown tasks
        entry = get_ledger_entry("workflow")
        return {
            "skill": "workflow",
            "confidence": 0.3,
            "reasoning": "No keyword match — defaulting to workflow skill.",
            "blocked": entry["CI"] < CI_BLOCKED,
            "block_reason": "workflow CI below threshold" if entry["CI"] < CI_BLOCKED else None,
            "CI": entry["CI"],
        }

    # Sort by match score desc, then CI desc
    candidates.sort(key=lambda x: (x[1], x[2]), reverse=True)
    best_skill, match_score, ci = candidates[0]

    confidence = min(0.4 + (match_score * 0.15), 0.95)
    blocked = ci < CI_BLOCKED
    block_reason = None
    if blocked:
        block_reason = f"{best_skill} CI ({ci}) is below {CI_BLOCKED} — requires human review"

    return {
        "skill": best_skill,
        "confidence": round(confidence, 2),
        "reasoning": f"Best match for task keywords (score={match_score}). "
        f"CI={ci} ({'trusted' if ci >= CI_FULL_TRUST else 'normal' if ci >= CI_NORMAL else 'restricted'}).",
        "blocked": blocked,
        "block_reason": block_reason,
        "CI": ci,
    }


def execute_skill(skill_path: str, task: str) -> dict:
    """
    Execute a skill after CI audit passes.
    skill_path: e.g. 'skills/core/workflow/SKILL.md'
    Returns: {status, output, ci_delta}
    """
    from datetime import datetime

    skill_file = SKILLS_DIR / skill_path
    if not skill_file.exists():
        return {"status": "error", "output": f"Skill not found: {skill_path}", "ci_delta": 0}

    skill_name = skill_path.split("/")[1]  # e.g. 'workflow' from 'core/workflow/SKILL.md'
    entry = get_ledger_entry(skill_name)

    if entry["CI"] < CI_BLOCKED:
        return {
            "status": "blocked",
            "output": f"Skill '{skill_name}' CI={entry['CI']} is below threshold. Human review required.",
            "ci_delta": 0,
        }

    # Skill execution would be handled by the agent reading SKILL.md
    # Here we return metadata for the routing agent to use
    return {
        "status": "ready",
        "skill": skill_name,
        "skill_file": str(skill_file),
        "CI": entry["CI"],
        "ci_delta": 0,  # delta applied by workflow skill after execution
    }


def update_ci(skill_name: str, delta: int) -> dict:
    """
    Update CI score for a skill in PERFORMANCE_LEDGER.md.
    Returns updated entry.
    """
    if not LEDGER_PATH.exists():
        return {"CI": 50, "error": "Ledger not found"}

    content = LEDGER_PATH.read_text()
    entry = get_ledger_entry(skill_name)
    new_ci = max(0, min(100, entry["CI"] + delta))
    new_tasks = entry["tasks_completed"] + (1 if delta > 0 else 0)
    from datetime import datetime

    new_active = datetime.now().strftime("%Y-%m-%d")

    # Regex replace the skill row
    pattern = re.compile(
        rf"(\|\s*{re.escape(skill_name)}\s*\|\s*)\d+(\s*\|\s*)\d+(\s*\|\s*)[^|]+(\s*\|)",
        re.IGNORECASE,
    )
    replacement = rf"\g<1>{new_ci}\g<2>{new_tasks}\g<3>{new_active}\4"
    new_content, count = pattern.subn(replacement, content)

    if count == 0:
        return {"CI": entry["CI"], "error": f"Skill '{skill_name}' not found in ledger"}

    LEDGER_PATH.write_text(new_content)
    return {"skill": skill_name, "CI": new_ci, "tasks_completed": new_tasks, "last_active": new_active}


def audit() -> dict:
    """
    Full system CI health check.
    Returns: {status, blocked_skills, healthy_skills, overall_ci}
    """
    entries = get_all_skill_entries()
    blocked = [s for s, d in entries.items() if d["CI"] < CI_BLOCKED]
    healthy = [s for s, d in entries.items() if d["CI"] >= CI_NORMAL]
    if entries:
        avg_ci = sum(d["CI"] for d in entries.values()) / len(entries)
    else:
        avg_ci = 50

    return {
        "status": "healthy" if not blocked else "degraded",
        "blocked_skills": blocked,
        "healthy_skills": healthy,
        "overall_ci": round(avg_ci, 1),
        "skill_count": len(entries),
    }
