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
CI_REHABILITATION = 20  # below this: rehabilitation mode (reduced confidence, not hard block)
CI_BLOCKED = 30  # hard block threshold (kept for compatibility)


def get_ledger_entry(skill_name: str) -> dict:
    """
    Retrieve CI score and stats for a skill from the PERFORMANCE_LEDGER.md.
    Returns: {CI: int, tasks_completed: int, last_active: str}
    Creates the ledger if it doesn't exist (initialized at CI=50 for all skills).
    """
    if not LEDGER_PATH.exists():
        _bootstrap_ledger()
        return {"CI": 50, "tasks_completed": 0, "last_active": "-"}

    content = LEDGER_PATH.read_text()

    # Find the skill row (case-insensitive)
    # Actual format: | Skill | CI | Last Active |  (3 columns)
    pattern = re.compile(
        rf"^\|\s*{re.escape(skill_name)}\s*\|\s*(\d+)\s*\|\s*([^*|\n][^\n]*?)\s*\|",
        re.IGNORECASE | re.MULTILINE,
    )
    match = pattern.search(content)
    if match:
        return {
            "CI": int(match.group(1)),
            "tasks_completed": 0,
            "last_active": match.group(2).strip().rstrip("|").strip(),
        }

    # Skill not in ledger — initialize at neutral CI
    return {"CI": 50, "tasks_completed": 0, "last_active": "-"}


def _bootstrap_ledger() -> None:
    """Create PERFORMANCE_LEDGER.md with CI=50 for all known skills (3-column format)."""
    skills = [
        "workflow", "context", "discovery", "spec",
        "acceptance_test", "orchestration", "engine", "memory",
    ]
    header = "| Skill | CI | Last Active |\n|---|---|---|\n"
    rows = "\n".join(f"| {s} | 50 | - |" for s in skills)
    try:
        lock = filelock.FileLock(str(LOCK_PATH), timeout=10)
        with lock:
            atomic_write(LEDGER_PATH, header + rows)
    except Exception:
        pass  # Best-effort: don't crash on bootstrap failure



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
    # Note: short keywords like "log" use word-boundary matching to avoid
    # false positives (e.g. "log" shouldn't match "login").
    # Format: (keyword, word_boundary: bool)
    skill_map = {
        "context":   [("context", False), ("load", False), ("inject", False),
                      ("priority", False), ("claude.md", False), ("compact", False),
                      ("compression", False), ("survive", False),
                      ("ide window", False), ("context window", False), ("token overhead", False)],
        "memory":    [("memory", False), ("archive", False), ("daily", False),
                      ("remember", False), ("recall", False), ("search", False),
                      ("prune", False), ("distill", False), ("cookbook", False), ("cookbooks", False),
                      ("decisions", False), ("learned", False), ("shipment", False),
                      ("shipments", False),
                      # word-boundary only for short ambiguous words
                      (" log ", True), (" log.", True), (" log,", True)],
        "workflow":  [("workflow", False), ("/explore", False), ("/spec", False),
                      ("/build", False), ("/verify", False), ("/ship", False),
                      ("/acceptance", False), ("/auto", False), ("step", False),
                      ("specification", False), ("5-step", False), ("pipeline", False),
                      ("user review", False), ("approve spec", False),
                      ("auto-confirm", False), ("auto confirm", False),
                      ("skip review", False), ("automatic approval", False),
                      ("implement", False), ("user story", False),
                      ("acceptance criteria", False), ("story point", False),
                      ("feature", False), ("new", False)],
        "orchestration": [("orchestrat", False), ("parallel", False), ("multi-agent", False),
                          ("agent team", False), ("swarm", False), ("concurrent", False),
                          ("batch", False), ("coordinate agents", False),
                          ("worktree", False), ("git worktree", False), ("divide work", False)],
        "engine":    [("engine", False), ("router", False), ("route", False),
                      ("ci", False), ("audit", False), ("observer", False),
                      ("dream", False), ("status", False), ("health", False),
                      ("stats", False), ("performance ledger", False), ("self-evolv", False)],
        "checkpoint":[("checkpoint", False), ("checkpointing", False), ("handoff", False),
                      ("resume", False), ("state save", False),
                      ("save progress", False), ("interrupt", False), ("session persist", False)],
        "discovery": [("discovery", False), ("interview", False), ("clarify", False),
                     ("questions", False), ("understand", False),
                     ("what i need", False), ("what do you want", False),
                     ("requirements", False), ("user story", False),
                     ("clarifying", False), ("ask questions", False),
                     ("/discovery", False), ("gather requirements", False)],
        "acceptance_test": [("acceptance", False), ("user test", False),
                           ("acceptance test", False), ("/acceptance", False),
                           ("run it", False), ("does it work", False),
                           ("user verification", False), ("pytest", False),
                           ("coverage", False), ("unit test", False),
                           ("integration test", False)],
        # Catch-all for coding tasks that don't match specific skills
        "wildcard":  [("bug", False), ("fix", False), ("crash", False),
                       ("error", False), ("debug", False), ("patch", False),
                       ("refactor", False), ("security", False), ("performance", False),
                       ("optimize", False), ("leak", False), ("race condition", False),
                       ("timeout", False), ("flake", False), ("lint", False),
                       ("type error", False), ("import error", False)],
    }

    candidates = []
    for skill, keywords in skill_map.items():
        score = 0
        for kw, wb in keywords:
            if wb:
                # Word boundary: kw padded with spaces to avoid substring false positives
                if f" {kw} " in f" {task_lower} " or task_lower.startswith(f"{kw} ") or task_lower.endswith(f" {kw}"):
                    score += 1
            else:
                if kw in task_lower:
                    score += 1
        if score > 0:
            entry = get_ledger_entry(skill)
            candidates.append((skill, score, entry["CI"]))

    # Wildcard: if task has bug/fix/error keywords but no specific skill matched,
    # treat it as a workflow task (fix a bug → build → verify → ship)
    if not candidates:
        wildcard_kws = skill_map["wildcard"]
        wc_score = sum(1 for kw, wb in wildcard_kws if kw in task_lower)
        if wc_score > 0:
            entry = get_ledger_entry("workflow")
            candidates.append(("workflow", wc_score, entry["CI"]))


    if not candidates:
        # Default to workflow for unknown tasks
        entry = get_ledger_entry("workflow")
        ci = entry["CI"]
        ci_status = (
            "trusted" if ci >= CI_FULL_TRUST
            else "normal" if ci >= CI_NORMAL
            else "restricted" if ci >= CI_REHABILITATION
            else "rehabilitation"
        )
        blocked = ci < CI_REHABILITATION
        return {
            "skill": "workflow",
            "confidence": 0.3,
            "reasoning": f"No keyword match — defaulting to workflow (CI={ci}, {ci_status}).",
            "blocked": blocked,
            "block_reason": f"workflow CI ({ci}) < {CI_REHABILITATION}" if blocked else None,
            "CI": ci,
            "CI_status": ci_status,
        }

    # Sort by match score desc, then CI desc (numeric, not lexicographic)
    candidates.sort(key=lambda x: (x[1], x[2] * 100), reverse=True)
    best_skill, match_score, ci = candidates[0]

    # CI-weighted confidence: 65% keyword match, 35% CI signal
    ci_factor = min(ci / CI_FULL_TRUST, 1.0)
    max_score = max(s for _, s, _ in candidates) if candidates else 1
    normalized_keyword = match_score / max_score if max_score > 0 else 0
    confidence = min(0.25 + (normalized_keyword * 0.35) + (ci_factor * 0.25), 0.95)

    # Rehabilitation vs blocked: CI 0-19 = rehabilitation (reduced confidence), CI 20-29 = restricted
    rehabilitation_mode = ci < CI_REHABILITATION
    restricted_mode = CI_REHABILITATION <= ci < CI_BLOCKED
    blocked = ci < CI_REHABILITATION  # only CI < 20 is truly blocked
    if rehabilitation_mode:
        confidence = confidence * 0.7  # 30% confidence penalty
        block_reason = f"{best_skill} CI ({ci}) < {CI_REHABILITATION} — rehabilitation mode: reduced confidence"
    elif restricted_mode:
        block_reason = f"{best_skill} CI ({ci}) < {CI_BLOCKED} — restricted mode: reduced confidence"
    else:
        block_reason = None

    ci_status = (
        "trusted" if ci >= CI_FULL_TRUST
        else "normal" if ci >= CI_NORMAL
        else "restricted" if ci >= CI_REHABILITATION
        else "rehabilitation"
    )
    result = {
        "skill": best_skill,
        "confidence": round(confidence, 2),
        "reasoning": f"Best match (score={match_score}, CI={ci}, {ci_status}). "
        f"Composite: 65% keyword + 35% CI signal.",
        "blocked": blocked,
        "block_reason": block_reason,
        "CI": ci,
        "CI_status": ci_status,
        "_rehabilitation_mode": rehabilitation_mode,
        "_restricted_mode": restricted_mode,
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
    Delegates to skill_execution.run() which now handles routing internally.

    NOTE: route_task() is now called inside skill_execution.run() — do NOT
    route here to avoid double-routing (route_task -> run -> route_task).

    skill_path: e.g. 'skills/core/workflow/SKILL.md'
    Returns: {status, output, ci_delta, skill, duration_ms, routing_confidence}
    """
    from engine import skill_execution
    # skill_path: 'skills/core/<name>/SKILL.md' — index 2 = skill name
    parts = skill_path.split("/")
    if len(parts) < 3:
        return {"status": "error", "output": f"Invalid skill_path: {skill_path!r}", "ci_delta": 0}
    skill_name = parts[2]
    # run() calls route_task() internally — no need to route here
    ctx = dict(context) if context else {}
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
        from datetime import datetime

        new_active = datetime.now().strftime("%Y-%m-%d")

        # Regex replace the skill row (3-column format: Skill | CI | Last Active)
        # Group 1: leading | and whitespace + skill name + | whitespace
        # Group 2: CI number + | whitespace
        # Group 3: Last Active text + trailing |
        pattern = re.compile(
            rf"(\|\s*{re.escape(skill_name)}\s*\|\s*)\d+(\s*\|\s*)[^\n]+?(\s*\|)",
            re.IGNORECASE,
        )
        replacement = rf"\g<1>{new_ci}\g<2>{new_active} |"
        new_content, count = pattern.subn(replacement, content)

        if count == 0:
            # Row doesn't exist — append it
            new_row = f"\n| {skill_name} | {new_ci} | {new_active} |"
            new_content = content.rstrip() + new_row
            count = 1
            return {"CI": entry["CI"], "last_active": "-", "error": f"Skill '{skill_name}' not found in ledger"}

        atomic_write(LEDGER_PATH, new_content)
        return {"skill": skill_name, "CI": new_ci, "last_active": new_active}


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
