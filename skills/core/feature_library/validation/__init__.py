"""
Feature Library Skill — Validation Module
run_validation() → {valid: bool, errors: list, warnings: list}
"""
from __future__ import annotations

import json
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
    for field in ["name:", "version:", "dependencies:"]:
        if field not in content[:500]:
            errors.append(f"Frontmatter missing: {field}")

    # 2. Logic module
    logic_init = skill_dir / "logic" / "__init__.py"
    if not logic_init.exists():
        errors.append("logic/__init__.py missing")
    else:
        logic_content = logic_init.read_text()
        if "route_feature" not in logic_content:
            errors.append("route_feature function not found")
        if "route_auth" not in logic_content:
            warnings.append("route_auth shortcut not found")
        if "route_api" not in logic_content:
            warnings.append("route_api shortcut not found")

    # 3. feature_library.json must exist
    json_path = skill_dir / "feature_library.json"
    if not json_path.exists():
        errors.append("feature_library.json missing")
    else:
        try:
            data = json.loads(json_path.read_text())
            if "categories" not in data:
                errors.append("feature_library.json missing 'categories' key")
            else:
                # Check for required categories
                cat_names = [c["id"] for c in data["categories"]]
                required_cats = ["auth", "api", "database", "realtime"]
                for req in required_cats:
                    if req not in cat_names:
                        errors.append(f"Missing required category: {req}")
                # Check patterns have required fields
                total_patterns = 0
                for cat in data["categories"]:
                    for pattern in cat.get("patterns", []):
                        total_patterns += 1
                        for field in ["name", "stack", "use_cases", "implementation"]:
                            if field not in pattern:
                                errors.append(
                                    f"Pattern '{pattern.get('name', '?')}' missing '{field}'"
                                )
                if total_patterns < 10:
                    warnings.append(f"Only {total_patterns} patterns — consider adding more")
        except json.JSONDecodeError as e:
            errors.append(f"feature_library.json is invalid JSON: {e}")

    # 4. Validation module
    val_mod = skill_dir / "validation" / "__init__.py"
    if not val_mod.exists():
        warnings.append("validation/__init__.py missing (this file)")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "warnings": warnings,
    }
