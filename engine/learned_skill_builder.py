"""
NEUTRON EVO OS — Learned Skill Builder
Distills reusable patterns from successful sessions into skills/learned/.

Learned skills: type=learned, initial CI=35 (degraded — prove yourself).
Lifecycle: learned (CI=35) → proven (CI≥50) → core (CI≥70)

CI delta rules for learned skills:
  - Learned skill invoked + reused successfully: +3 CI
  - Learned skill promoted to core: +10 CI (major milestone)
  - Learned skill not used in 30 days: -2 CI
"""
from __future__ import annotations

import json
import os
import re
import shutil
import filelock
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from engine._atomic import atomic_write

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
LEARNED_DIR = NEUTRON_ROOT / "skills" / "learned"
MEMORY_DIR = NEUTRON_ROOT / "memory"
INVOCATION_LOG = MEMORY_DIR / ".learned_invocations.json"
INVOCATION_LOCK = MEMORY_DIR / ".learned_invocations.lock"

# ─── Invocation tracking ─────────────────────────────────────────────────────────

def _load_invocations() -> dict:
    if INVOCATION_LOG.exists():
        try:
            return json.loads(INVOCATION_LOG.read_text())
        except Exception:
            pass
    return {}


def _save_invocations(data: dict):
    """Save invocation log atomically (filelock + fsync + rename)."""
    MEMORY_DIR.mkdir(exist_ok=True)
    lock = filelock.FileLock(str(INVOCATION_LOCK), timeout=10)
    with lock:
        atomic_write(INVOCATION_LOG, json.dumps(data, indent=2))


def _record_invocation(skill_name: str):
    """Record that a learned skill was invoked."""
    inv = _load_invocations()
    now = datetime.now().isoformat()
    inv[skill_name] = {
        "last_invoked": now,
        "count": inv.get(skill_name, {}).get("count", 0) + 1,
    }
    _save_invocations(inv)


# ─── Pattern distillation ────────────────────────────────────────────────────────

def _scan_memory_for_patterns(days: int = 14) -> list[dict]:
    """
    Scan recent memory logs for recurring patterns/decisions.
    Returns list of {pattern, frequency, last_seen, context}.
    """
    cutoff = datetime.now() - timedelta(days=days)
    patterns: dict[str, dict] = {}

    for log_file in MEMORY_DIR.glob("????-??-??.md"):
        try:
            mtime = datetime.fromtimestamp(log_file.stat().st_mtime)
            if mtime < cutoff:
                continue
        except Exception:
            continue

        try:
            content = log_file.read_text(errors="ignore")
        except Exception:
            continue

        # Extract decision/outcome lines
        for line in content.splitlines():
            stripped = line.strip()
            # Key markers: task outcomes, decision lines, successful patterns
            if any(kw in stripped for kw in ["Task:", "Outcome:", "CI delta:", "Action:"]):
                # Normalize
                key = re.sub(r"\[\d{2}:\d{2}\]\s*", "", stripped)
                key = re.sub(r"\d{4}-\d{2}-\d{2}", "[DATE]", key)
                key = key[:120]
                if key and len(key) > 20:
                    if key not in patterns:
                        patterns[key] = {"pattern": stripped, "frequency": 0, "last_seen": ""}
                    patterns[key]["frequency"] += 1
                    patterns[key]["last_seen"] = log_file.stem

        # Extract skill execution patterns
        skill_matches = re.findall(r"Skill:\s+(\w+)", content)
        for skill in skill_matches:
            key = f"skill:{skill}"
            if key not in patterns:
                patterns[key] = {"pattern": f"Skill execution: {skill}", "frequency": 0, "last_seen": ""}
            patterns[key]["frequency"] += 1
            patterns[key]["last_seen"] = log_file.stem

    # Sort by frequency descending
    return sorted(patterns.values(), key=lambda x: -x["frequency"])


def distill_patterns(days: int = 14, top_n: int = 5) -> list[dict]:
    """
    Return top N most frequent patterns from recent memory.
    Candidates for learned skill creation.
    """
    patterns = _scan_memory_for_patterns(days)
    return patterns[:top_n]


# ─── Skill registration ────────────────────────────────────────────────────────

def _slugify(name: str) -> str:
    """Convert a pattern name into a valid directory slug."""
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower())
    slug = re.sub(r"^-|-$", "", slug)
    return slug[:60]


def register_learned_skill(
    name: str,
    pattern: str,
    when_to_apply: str,
    example: str = "",
    notes: str = "",
    source_pattern: str = "",
) -> dict:
    """
    Write a new learned skill to skills/learned/<slug>/SKILL.md.

    Creates directory structure + SKILL.md with full frontmatter.
    """
    slug = _slugify(name)
    skill_dir = LEARNED_DIR / slug
    skill_md = skill_dir / "SKILL.md"
    logic_init = skill_dir / "logic" / "__init__.py"
    validation_init = skill_dir / "validation" / "__init__.py"

    if skill_md.exists():
        return {"status": "already_exists", "slug": slug, "path": str(skill_md)}

    # Create directories
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "logic").mkdir(exist_ok=True)
    (skill_dir / "validation").mkdir(exist_ok=True)

    # Write SKILL.md
    today = datetime.now().strftime("%Y-%m-%d")
    skill_content = f"""---
name: {slug}
type: learned
version: 0.1.0
CI: 35
dependencies: []
last_dream: {today}
---

## Learned Skill: {name}

### Pattern
{pattern}

### When to Apply
{when_to_apply}

### Example
{example}

### Notes
{notes}
"""
    if source_pattern:
        skill_content += f"\n### Source\nDistilled from: {source_pattern}\n"

    skill_md.write_text(skill_content)

    # Write logic stub
    logic_init.write_text(f'''"""Learned Skill: {name}"""
from __future__ import annotations

def run_learned_{slug}(task: str, context: dict = None) -> dict:
    """
    Learned skill: {name}
    type: learned | initial CI: 35
    """
    from engine.skill_registry import discover_learned_skills
    from engine.expert_skill_router import update_ci

    # Record invocation
    _record_invocation("{slug}")

    # Execute the skill logic
    result = {{"status": "ok", "output": "{name}", "ci_delta": 3}}

    # Update CI
    update_ci("{slug}", 3)
    return result
''')

    # Write validation stub
    validation_init.write_text(f'''"""Learned Skill Validation: {name}"""
from __future__ import annotations
from typing import Union

def validate_learned_{slug}(inputs: dict) -> Union[bool, str]:
    return True
''')

    # Record invocation
    _record_invocation(slug)

    return {
        "status": "registered",
        "slug": slug,
        "path": str(skill_md),
        "skill_dir": str(skill_dir),
        "CI": 35,
    }


# ─── Main API ──────────────────────────────────────────────────────────────────

def run_learn(task: str, context: dict = None) -> dict:
    """
    Main entry point. Actions:
      distill : scan memory → return top patterns as candidates
      register : create a learned skill from pattern data
      list    : show all learned skills + invocation stats
      invoke  : invoke a learned skill by name
      promote : promote a learned skill to core (CI ≥ 50 required)
    """
    context = context or {}
    action = context.get("action", "list")

    if action == "distill":
        return _action_distill(context)
    elif action == "register":
        return _action_register(context)
    elif action == "list":
        return _action_list()
    elif action == "invoke":
        return _action_invoke(task, context)
    elif action == "promote":
        return _action_promote(task, context)
    elif action == "stale":
        return _action_stale()
    else:
        return {"status": "error", "output": f"Unknown action: {action}", "ci_delta": 0}


def _action_distill(context: dict) -> dict:
    days = context.get("days", 14)
    top_n = context.get("top_n", 5)
    patterns = distill_patterns(days=days, top_n=top_n)
    if not patterns:
        return {
            "status": "no_patterns",
            "output": f"No recurring patterns found in last {days} days of memory.",
            "candidates": [],
        }
    lines = [f"## Pattern Candidates (from {days}-day memory scan)"]
    for i, p in enumerate(patterns, 1):
        lines.append(f"\n{i}. *\"{p['pattern'][:100]}\"")
        lines.append(f"   Frequency: {p['frequency']}x | Last: {p['last_seen']}")
    return {
        "status": "candidates",
        "output": "\n".join(lines),
        "candidates": patterns,
    }


def _action_register(context: dict) -> dict:
    required = ["name", "pattern", "when_to_apply"]
    for field in required:
        if not context.get(field):
            return {"status": "error", "output": f"Missing required field: {field}", "ci_delta": 0}
    return register_learned_skill(
        name=context["name"],
        pattern=context["pattern"],
        when_to_apply=context["when_to_apply"],
        example=context.get("example", ""),
        notes=context.get("notes", ""),
        source_pattern=context.get("source_pattern", ""),
    )


def _action_list() -> dict:
    from engine.skill_registry import discover_learned_skills

    skills = discover_learned_skills()
    inv = _load_invocations()
    now = datetime.now()
    stale_threshold = timedelta(days=30)

    if not skills:
        return {
            "status": "no_learned_skills",
            "output": "No learned skills yet. Run: learned(action='distill') to find candidates.",
        }

    lines = [f"## Learned Skills ({len(skills)})"]
    lines.append(f"  Initial CI: 35 | Proven at CI≥50 | Core at CI≥70")
    lines.append("")
    for name, skill in sorted(skills.items()):
        slug = skill.get("slug", name)
        ci = int(skill.get("frontmatter", {}).get("CI", 35))
        inv_data = inv.get(slug, {})
        last_invoked = inv_data.get("last_invoked", "never")
        count = inv_data.get("count", 0)
        ci_bar = "█" * (ci // 10) + "░" * (10 - ci // 10)
        status = "✅ proven" if ci >= 50 else "🟡 learning"
        if last_invoked != "never":
            try:
                last_dt = datetime.fromisoformat(last_invoked)
                if (now - last_dt) > stale_threshold:
                    status = "⚠️ stale"
            except Exception:
                pass
        lines.append(f"  [{status}] {name}")
        lines.append(f"     CI: {ci_bar} {ci} | Used: {count}x | Last: {last_invoked[:10]}")

    return {
        "status": "ok",
        "output": "\n".join(lines),
        "skills": list(skills.keys()),
        "invocations": inv,
    }


def _action_invoke(task: str, context: dict) -> dict:
    skill_name = context.get("skill_name", task.split()[0] if task else "")
    if not skill_name:
        return {"status": "error", "output": "skill_name required in context", "ci_delta": 0}

    from engine.skill_registry import discover_learned_skills, get_skill
    from engine import skill_execution

    skills = discover_learned_skills()
    if skill_name not in skills:
        return {"status": "not_found", "output": f"Learned skill not found: {skill_name}", "ci_delta": 0}

    # Record invocation + CI update
    _record_invocation(skill_name)

    # Try to execute via skill_execution
    try:
        result = skill_execution.run("learned", task, {"skill": skill_name, **context})
        return result
    except Exception as e:
        return {"status": "error", "output": f"Execution failed: {e}", "ci_delta": -2}


def _action_promote(task: str, context: dict) -> dict:
    """Promote a learned skill to core (requires CI ≥ 50)."""
    from engine.expert_skill_router import update_ci

    skill_name = context.get("skill_name", "")
    if not skill_name:
        return {"status": "error", "output": "skill_name required in context", "ci_delta": 0}

    from engine.skill_registry import discover_learned_skills
    skills = discover_learned_skills()
    if skill_name not in skills:
        return {"status": "not_found", "output": f"Learned skill not found: {skill_name}", "ci_delta": 0}

    skill = skills[skill_name]
    ci = int(skill.get("frontmatter", {}).get("CI", 35))

    if ci < 50:
        return {
            "status": "blocked",
            "output": f"Cannot promote: CI={ci} < 50 (needs CI≥50 first)",
            "ci_delta": 0,
        }

    # Move to core
    slug = skill.get("slug", skill_name)
    learned_dir = skill["dir"]
    core_dir = NEUTRON_ROOT / "skills" / "core" / slug

    if core_dir.exists():
        return {"status": "error", "output": f"Core skill already exists: {slug}", "ci_delta": 0}

    shutil.copytree(learned_dir, core_dir)

    # Update SKILL.md in core
    core_md = core_dir / "SKILL.md"
    content = core_md.read_text()
    content = content.replace('type: learned', 'type: core')
    content = re.sub(r"^CI: \d+", "CI: 70", content, flags=re.MULTILINE)
    core_md.write_text(content)

    # Update CI +10
    update_ci(slug, 10)

    return {
        "status": "promoted",
        "output": f"✅ {skill_name} promoted to core (CI=70). Learned entry removed.",
        "ci_delta": 10,
        "new_path": str(core_dir),
    }


def _action_stale() -> dict:
    """Show learned skills not invoked in 30+ days."""
    inv = _load_invocations()
    now = datetime.now()
    stale_threshold = timedelta(days=30)

    stale = []
    for skill_name, inv_data in inv.items():
        last = inv_data.get("last_invoked", "")
        if not last or last == "never":
            stale.append(skill_name)
            continue
        try:
            last_dt = datetime.fromisoformat(last)
            if (now - last_dt) > stale_threshold:
                stale.append(skill_name)
        except Exception:
            stale.append(skill_name)

    if stale:
        return {
            "status": "stale",
            "output": f"⚠️  {len(stale)} learned skills not invoked in 30+ days: {', '.join(stale)}",
            "stale_skills": stale,
        }
    return {"status": "ok", "output": "No stale learned skills.", "stale_skills": []}
