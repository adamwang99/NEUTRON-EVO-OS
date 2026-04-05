"""
SPEC Skill — Validation Module
run_validation() → {valid: bool, errors: list, warnings: list}
"""
from __future__ import annotations

import re
from pathlib import Path


def run_validation() -> dict:
    errors = []
    warnings = []

    skill_dir = Path(__file__).parent.parent
    root = skill_dir.parent.parent.parent

    # 1. SKILL.md must exist
    skill_md = skill_dir / "SKILL.md"
    if not skill_md.exists():
        errors.append("SKILL.md missing")
        return {"valid": False, "errors": errors, "warnings": warnings}

    content = skill_md.read_text()

    # 2. Must have required frontmatter fields
    required_frontmatter = ["name:", "version:", "dependencies:"]
    for field in required_frontmatter:
        if field not in content[:500]:
            errors.append(f"Frontmatter missing required field: {field}")

    # 3. Must have Round 1, Round 2, Round 3 described
    for round_name in ["ROUND 1", "ROUND 2", "ROUND 3"]:
        if round_name not in content.upper():
            errors.append(f"Missing round description: {round_name}")

    # 4. Must have USER APPROVAL GATE
    if "APPROVE" not in content or "HARD GATE" not in content.upper():
        errors.append("Missing USER APPROVAL GATE")

    # 5. Must reference discovery skill
    if "discovery" not in content.lower():
        warnings.append("Does not explicitly reference discovery skill")

    # 6. Logic module must exist
    logic_init = skill_dir / "logic" / "__init__.py"
    if not logic_init.exists():
        errors.append("logic/__init__.py missing")

    # 7. run_spec_skill must be defined
    if logic_init.exists():
        logic_content = logic_init.read_text()
        if "run_spec_skill" not in logic_content:
            errors.append("run_spec_skill function not found in logic/__init__.py")
        if "def _lint_spec" not in logic_content:
            warnings.append("No spec linting function found")
        if "def _generate_round1" not in logic_content:
            warnings.append("No round1 question generator found")

    # 8. Validation module should exist
    val_mod = skill_dir / "validation" / "__init__.py"
    if not val_mod.exists():
        warnings.append("validation/__init__.py missing (this file)")

    # 9. Check debate rounds are properly ordered
    round_order = ["round1", "round2", "round3"]
    for rt in round_order:
        if f"def _{rt}" not in content.lower() and rt.upper() not in content.upper():
            warnings.append(f"Round {rt} not clearly documented")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
