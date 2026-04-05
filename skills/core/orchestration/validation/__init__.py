"""
Orchestration Skill — Validation Module
run_validation() → {valid: bool, errors: list, warnings: list}
"""
from __future__ import annotations

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

    # 2. Must have required frontmatter
    for field in ["name:", "version:", "dependencies:"]:
        if field not in content[:500]:
            errors.append(f"Frontmatter missing: {field}")

    # 3. Must have all 7 phases documented
    phases = ["analyze", "plan", "execute", "merge", "report"]
    for phase in phases:
        if phase not in content.lower():
            errors.append(f"Missing phase documentation: {phase}")

    # 4. Must mention conflict prevention
    if "conflict" not in content.lower():
        warnings.append("No conflict prevention rules documented")

    # 5. Must reference agent types
    if "agent" not in content.lower():
        warnings.append("No agent type references found")

    # 6. Logic module
    logic_init = skill_dir / "logic" / "__init__.py"
    if not logic_init.exists():
        errors.append("logic/__init__.py missing")
    else:
        logic_content = logic_init.read_text()
        if "run_orchestration" not in logic_content:
            errors.append("run_orchestration function not found")
        for fn in ["_analyze_complexity", "_decompose_task", "_detect_conflicts"]:
            if fn not in logic_content:
                warnings.append(f"Missing function: {fn}")

    # 7. Validation module
    val_mod = skill_dir / "validation" / "__init__.py"
    if not val_mod.exists():
        warnings.append("validation/__init__.py missing (this file)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
