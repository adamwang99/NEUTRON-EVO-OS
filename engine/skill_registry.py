"""
NEUTRON-EVO-OS: Skill Registry
Dynamically discovers and registers all core skills from SKILL.md frontmatter.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
SKILLS_DIR = NEUTRON_ROOT / "skills" / "core"

# Module-level registry cache
_registry: dict = {}


def _parse_frontmatter(file_path: Path) -> dict:
    """Parse YAML frontmatter from a SKILL.md file."""
    if not file_path.exists():
        return {}
    text = file_path.read_text()
    match = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not match:
        return {}
    result = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            result[key.strip()] = value.strip()
    return result


def _is_real_module(init_file: Path) -> bool:
    """True if the __init__.py has real content (not just a stub comment)."""
    if not init_file.exists():
        return False
    content = init_file.read_text().strip()
    # Stubs are < 50 chars; real modules have actual code
    return len(content) > 50


def discover_skills() -> dict:
    """
    Scan skills/core/*/SKILL.md, parse frontmatter, cache registry.
    Returns: {skill_name: {dir, frontmatter, has_logic, has_validation}}
    """
    global _registry
    if _registry:
        return _registry

    for skill_dir in SKILLS_DIR.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        fm = _parse_frontmatter(skill_md)
        name = fm.get("name", skill_dir.name)

        _registry[name] = {
            "dir": skill_dir,
            "frontmatter": fm,
            "has_logic": _is_real_module(skill_dir / "logic" / "__init__.py"),
            "has_validation": _is_real_module(skill_dir / "validation" / "__init__.py"),
        }

    return _registry


def get_skill(skill_name: str) -> Optional[dict]:
    """Get a registered skill by name, or None if not found."""
    if not _registry:
        discover_skills()
    return _registry.get(skill_name)


def list_skills() -> list[str]:
    """Return all registered skill names."""
    if not _registry:
        discover_skills()
    return list(_registry.keys())


def has_logic(skill_name: str) -> bool:
    """True if the skill has a non-stub logic module."""
    skill = get_skill(skill_name)
    return bool(skill and skill["has_logic"])
