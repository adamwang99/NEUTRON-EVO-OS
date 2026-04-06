"""
NEUTRON-EVO-OS: Expert Skill Router
Audits PERFORMANCE_LEDGER.md before executing any skill.
Routes tasks to appropriate skills based on CI scores and availability.
"""
from __future__ import annotations

import os
import re
import filelock
from pathlib import Path
from typing import Optional

from engine._atomic import atomic_write

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
LEDGER_PATH = NEUTRON_ROOT / "PERFORMANCE_LEDGER.md"
LOCK_PATH = LEDGER_PATH.with_suffix(".lock")
SKILLS_DIR = NEUTRON_ROOT / "skills"

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
    # Support both 4-col format (skill|CI|tasks|last_active) and 2-col format (skill|CI)
    pattern = re.compile(
        r"^\|\s*(\w+)\s*\|\s*(\d+)\s*\|",
        re.MULTILINE,
    )
    for match in pattern.finditer(content):
        skill = match.group(1)
        entries[skill] = {
            "CI": int(match.group(2)),
            "tasks_completed": 0,
            "last_active": "-",
        }
    return entries


def _find_matching_learned_skills(task: str) -> list[dict]:
    """
    Check if any registered learned skill matches task keywords.
    This enables AUTO-INVOKE of learned skills — not just manual invocation.

    Returns: list of {slug, score, tags} sorted by score desc.
    Match score >= 0.7 = strong match, suggest as primary routing target.
    """
    import json
    learned_dir = SKILLS_DIR / "learned"
    if not learned_dir.exists():
        return []

    keywords = set(re.findall(r'\w{4,}', task.lower()))
    scored = []

    for skill_dir in learned_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        meta_file = skill_dir / ".meta.json"
        if not meta_file.exists():
            continue
        try:
            meta = json.loads(meta_file.read_text())
            tags = set(meta.get("tags", []))
            slug_words = set(re.findall(r'\w{4,}', skill_dir.name.lower()))
            overlap = keywords & (tags | slug_words)
            if len(overlap) >= 2:
                denom = len(keywords | (tags | slug_words))
                score = len(overlap) / denom if denom else 0
                if score >= 0.3:  # minimum threshold
                    scored.append({"slug": skill_dir.name, "score": score, "tags": list(tags)})
        except Exception:
            continue

    return sorted(scored, key=lambda x: x["score"], reverse=True)


def route_task(task: str, context: dict = None) -> dict:
    """
    Route a task to the best matching skill.
    Performs pre-route CI audit + learned skill auto-match.

    Returns: {skill, confidence, reasoning, blocked, block_reason, learned_skill}
    """
    from datetime import datetime

    task_lower = task.lower()
    context = context or {}

    # --- Skill mapping ---
    skill_map = {
        "context":   ["context", "load", "inject", "priority", "claude.md", "ide window",
                      "compact", "compression", "survive"],
        "memory":    ["memory", "log", "archive", "daily", "remember", "recall",
                      "search", "prune", "distill", "cookbook", "cookbooks", "decisions"],
        "workflow":  ["workflow", "/explore", "/spec", "/build", "/verify", "/ship",
                      "/acceptance", "/auto", "step", "specification", "5-step", "pipeline",
                      "user review", "approve spec", "auto-confirm", "auto confirm",
                      "skip review", "automatic approval"],
        "engine":    ["engine", "router", "route", "ci", "audit", "observer", "dream",
                      "status", "health", "stats", "performance ledger"],
        "checkpoint":["checkpoint", "checkpointing", "handoff", "resume", "state save"],
        "discovery": ["discovery", "interview", "clarify", "questions", "understand",
                      "what i need", "what do you want", "requirements", "user story",
                      "clarifying", "ask questions", "/discovery"],
        "acceptance_test": ["acceptance", "test", "verify", "user test", "acceptance test",
                           "/acceptance", "run it", "does it work", "user verification"],
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

    # Sort by match score desc, then CI desc (numeric, not lexicographic)
    candidates.sort(key=lambda x: (x[1], x[2] * 100), reverse=True)
    best_skill, match_score, ci = candidates[0]

    confidence = min(0.4 + (match_score * 0.15), 0.95)
    blocked = ci < CI_BLOCKED
    block_reason = None
    if blocked:
        block_reason = f"{best_skill} CI ({ci}) is below {CI_BLOCKED} — requires human review"

    result = {
        "skill": best_skill,
        "confidence": round(confidence, 2),
        "reasoning": f"Best match for task keywords (score={match_score}). "
        f"CI={ci} ({'trusted' if ci >= CI_FULL_TRUST else 'normal' if ci >= CI_NORMAL else 'restricted'}).",
        "blocked": blocked,
        "block_reason": block_reason,
        "CI": ci,
        "_routing_confidence": round(confidence, 2),
        "learned_skill": None,
    }

    # Learned skill auto-match: suggest if strong keyword match
    if confidence >= 0.55:
        learned_matches = _find_matching_learned_skills(task)
        if learned_matches:
            top = learned_matches[0]
            if top["score"] >= 0.7:
                result["learned_skill"] = top["slug"]
                result["learned_match_score"] = round(top["score"], 2)
                result["learned_tags"] = top["tags"]

    return result


def execute_skill(skill_path: str, task: str, context: dict = None) -> dict:
    """
    Execute a skill after CI audit passes.
    Delegates to skill_execution.run() for the actual logic.
    skill_path: e.g. 'skills/core/workflow/SKILL.md'
    Returns: {status, output, ci_delta, skill, duration_ms}
    """
    from engine import skill_execution
    # skill_path: 'skills/core/<name>/SKILL.md' — index 2 = skill name
    # Guard: validate path has at least 3 segments before split
    parts = skill_path.split("/")
    if len(parts) < 3:
        return {"status": "error", "output": f"Invalid skill_path: {skill_path!r}", "ci_delta": 0}
    skill_name = parts[2]
    # Route first to get confidence score
    route_result = route_task(task, context)
    ctx = dict(context) if context else {}
    ctx["_routing_confidence"] = route_result.get("confidence", 1.0)
    return skill_execution.run(skill_name, task, ctx)


def update_ci(skill_name: str, delta: int) -> dict:
    """
    Update CI score for a skill in PERFORMANCE_LEDGER.md.
    Returns updated entry. Thread/process safe via file lock.
    """
    if not LEDGER_PATH.exists():
        return {"CI": 50, "error": "Ledger not found"}

    lock = filelock.FileLock(str(LOCK_PATH), timeout=10)
    with lock:
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

        atomic_write(LEDGER_PATH, new_content)
        return {"skill": skill_name, "CI": new_ci, "tasks_completed": new_tasks, "last_active": new_active}


def audit() -> dict:
    """
    Full system CI health check.
    Returns: {status, blocked_skills, healthy_skills, overall_ci, rating_summary}
    """
    entries = get_all_skill_entries()
    blocked = [s for s, d in entries.items() if d["CI"] < CI_BLOCKED]
    healthy = [s for s, d in entries.items() if d["CI"] >= CI_NORMAL]
    if entries:
        avg_ci = sum(d["CI"] for d in entries.values()) / len(entries)
    else:
        avg_ci = 50

    # Include rating summary from rating system
    try:
        from engine.rating import summarize as rating_summarize
        rating_summary = rating_summarize()
    except Exception:
        rating_summary = None

    return {
        "status": "healthy" if not blocked else "degraded",
        "blocked_skills": blocked,
        "healthy_skills": healthy,
        "overall_ci": round(avg_ci, 1),
        "skill_count": len(entries),
        "rating_summary": rating_summary,
    }
