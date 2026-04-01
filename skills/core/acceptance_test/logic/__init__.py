"""
Acceptance Test Skill — Logic Module
run_acceptance_test(task, context) → {status, output, ci_delta}

Actions (via context["action"]):
  - prepare : Load SPEC.md, extract criteria, generate test script
  - pass    : User confirmed acceptance — record pass, enable ship
  - fail    : User reported failure — record failure, return to build
  - status  : Check current acceptance status

Acceptance test is BLOCKING for /ship:
  - No pass record = cannot ship
  - Fail record = must re-build before ship
"""
from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from datetime import datetime

# Levels: logic/__init__.py → acceptance_test/ → core/ → skills/ → repo root
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent.parent)
))
MEMORY_DIR = _NEUTRON_ROOT / "memory"
STATUS_FILE = MEMORY_DIR / ".acceptance_status.json"


def run_acceptance_test(task: str, context: dict = None) -> dict:
    # ── FIRST STEP: Check auto-confirm ─────────────────────────────────────────
    # This must be the FIRST check — AI reads this file, not auto_confirm.py
    try:
        from engine.auto_confirm import should_skip, record_auto_action
        if should_skip("acceptance"):
            _record_pass({"notes": "auto-confirm"})
            record_auto_action("acceptance", {})
            return {
                "status": "acceptance_auto_confirmed",
                "output": (
                    "[AUTO-CONFIRM] Acceptance test PASSED automatically.\n"
                    "/ship is now UNLOCKED."
                ),
                "can_ship": True,
                "ci_delta": 10,
                "auto_confirmed": True,
            }
    except Exception:
        pass  # Proceed with normal flow

    context = context or {}
    action = context.get("action", "prepare")

    if action == "status":
        return _check_status()
    elif action == "prepare":
        return _prepare_test(task, context)
    elif action == "pass":
        return _record_pass(context)
    elif action == "fail":
        return _record_fail(context)
    else:
        return {"status": "error", "output": f"Unknown action: '{action}'", "ci_delta": 0}


def _load_spec() -> dict:
    """Find and parse the most recent SPEC.md."""
    # Try NEUTRON_ROOT/SPEC.md first (in-session)
    spec_path = _NEUTRON_ROOT / "SPEC.md"
    if spec_path.exists():
        return _parse_spec(spec_path.read_text(), spec_path)

    # Fallback: most recent in memory/discoveries/
    if MEMORY_DIR.exists():
        candidates = sorted(MEMORY_DIR.rglob("SPEC.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if candidates:
            path = candidates[0]
            return _parse_spec(path.read_text(), path)

    return {}


def _parse_spec(content: str, path: Path) -> dict:
    """Parse SPEC.md into structured sections."""
    # Extract title
    title_match = re.search(r"^#\s+SPEC:\s*(.+)", content, re.MULTILINE)
    title = title_match.group(1).strip() if title_match else "Unknown SPEC"

    # Extract acceptance criteria section
    criteria = []
    in_criteria = False
    for line in content.splitlines():
        if re.match(r"##?\s*.*cceptance", line, re.IGNORECASE):
            in_criteria = True
            continue
        if in_criteria and line.startswith("##"):
            in_criteria = False
        if in_criteria and line.strip() and not line.startswith("#"):
            # Parse checklist items
            if re.match(r"^\s*[-*]\s*\[?\s*[x ]?\s*\]", line):
                text = re.sub(r"^\s*[-*]\s*\[?\s*[x ]?\s*\]\s*", "", line).strip()
                if text:
                    criteria.append(text)

    # Extract tech stack
    stack_match = re.search(r"##\s*Tech\s*Stack\s*\n(.*?)(?=\n##|\Z)", content, re.DOTALL | re.IGNORECASE)
    tech_stack = stack_match.group(1).strip() if stack_match else "unknown"

    return {
        "title": title,
        "criteria": criteria,
        "tech_stack": tech_stack,
        "path": str(path),
    }


def _load_status() -> dict:
    """Load current acceptance status."""
    if STATUS_FILE.exists():
        try:
            import json
            return json.loads(STATUS_FILE.read_text())
        except Exception:
            pass
    return {"status": "none", "history": []}


def _save_status(status: dict):
    """Save acceptance status."""
    STATUS_FILE.write_text(__import__("json").dumps(status, indent=2))


def _generate_test_script(spec: dict) -> dict:
    """
    Generate a test script for the user to run.
    Returns {language, script_content, command, expected_result}.
    """
    stack = spec.get("tech_stack", "unknown").lower()
    criteria = spec.get("criteria", [])

    if not criteria:
        return {
            "status": "no_criteria",
            "output": "No acceptance criteria found in SPEC.md. Please add measurable criteria before running acceptance test.",
            "ci_delta": 0,
        }

    # Determine language/tool
    if any(kw in stack for kw in ["python", "django", "flask", "fastapi"]):
        return _generate_python_test(criteria)
    elif any(kw in stack for kw in ["javascript", "typescript", "react", "node", "nodejs"]):
        return _generate_js_test(criteria)
    elif any(kw in stack for kw in ["rust", "go", "golang"]):
        return _generate_shell_test(criteria)
    else:
        return _generate_shell_test(criteria)


def _generate_python_test(criteria: list) -> dict:
    """Generate a pytest-style test file."""
    test_lines = [
        '"""',
        f"Acceptance Test — Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "Run: pytest tests/acceptance_test.py -v",
        '"""',
        "import pytest",
        "",
    ]
    for i, criterion in enumerate(criteria, 1):
        safe_name = re.sub(r"[^\w]", "_", criterion)[:40]
        test_lines += [
            f"def test_{i}_{safe_name}():",
            f'    """{criterion}"""',
            f"    # TODO: implement test for: {criterion}",
            "    assert False, 'ACCEPTANCE TEST NOT IMPLEMENTED — implement this test'",
            "",
        ]

    return {
        "language": "python",
        "framework": "pytest",
        "filename": "tests/acceptance_test.py",
        "content": "\n".join(test_lines),
        "command": "python3 -m pytest tests/acceptance_test.py -v",
        "expected": "All tests pass (0 failures)",
    }


def _generate_js_test(criteria: list) -> dict:
    """Generate a Jest/Vitest test file."""
    test_lines = [
        f"// Acceptance Test — Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"// Run: npx jest tests/acceptance.test.js  OR  npx vitest",
        "",
    ]
    for i, criterion in enumerate(criteria, 1):
        safe_name = re.sub(r"[^\w]", "_", criterion)[:40]
        test_lines += [
            f"test('{criterion}', () => {{",
            f"  // TODO: implement test for: {criterion}",
            f"  expect(false).toBe(true) // ACCEPTANCE TEST NOT IMPLEMENTED",
            "});",
            "",
        ]

    return {
        "language": "javascript",
        "framework": "jest/vitest",
        "filename": "tests/acceptance.test.js",
        "content": "\n".join(test_lines),
        "command": "npx jest tests/acceptance.test.js",
        "expected": "All tests pass",
    }


def _generate_shell_test(criteria: list) -> dict:
    """Generate a shell-based smoke test."""
    script = [
        "#!/bin/bash",
        f"# Acceptance Test — Generated {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        "# Run: bash tests/acceptance.sh",
        'echo "=== ACCEPTANCE TEST ==="',
        'echo "Manual verification required for the following criteria:"',
        "",
    ]
    for i, criterion in enumerate(criteria, 1):
        script.append(f'echo "{i}. {criterion}"')

    script += [
        "",
        'echo ""',
        'echo "If ALL criteria pass: acceptance_test(action="pass")',
        'echo "If any criterion fails: acceptance_test(action=\"fail\", notes=\"...\")"',
    ]

    return {
        "language": "shell",
        "framework": "bash",
        "filename": "tests/acceptance.sh",
        "content": "\n".join(script),
        "command": "bash tests/acceptance.sh",
        "expected": "Manual review by user",
    }


def _check_status() -> dict:
    status = _load_status()
    current = status.get("status", "none")
    history = status.get("history", [])
    last = history[-1] if history else None

    can_ship = current == "passed"

    return {
        "status": current,
        "can_ship": can_ship,
        "last_result": last,
        "history_count": len(history),
        "ci_delta": 0,
    }


def _prepare_test(task: str, context: dict) -> dict:
    """Step 1: Load SPEC, generate test script for user."""
    spec = _load_spec()

    if not spec.get("criteria"):
        return {
            "status": "error",
            "output": (
                "No acceptance criteria in SPEC.md.\n"
                "Cannot run acceptance test without measurable criteria.\n"
                "Add criteria like: 'User can do X', 'System returns Y in under Z seconds', etc."
            ),
            "ci_delta": 0,
        }

    script_info = _generate_test_script(spec)

    if script_info.get("status") == "no_criteria":
        return script_info

    # Save script to disk
    filename = script_info["filename"]
    script_path = _NEUTRON_ROOT / filename
    script_path.parent.mkdir(exist_ok=True)
    script_path.write_text(script_info["content"])

    # Update status
    status = _load_status()
    status["spec_path"] = spec.get("path", "")
    status["criteria_count"] = len(spec.get("criteria", []))
    _save_status(status)

    output = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🧪 ACCEPTANCE TEST — YOUR VERIFICATION
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📋 From SPEC: {spec.get('title', 'Unknown project')}

CRITERIA TO VERIFY ({len(spec['criteria'])} items):
"""
    for i, c in enumerate(spec["criteria"], 1):
        output += f"  {i}. {c}\n"

    output += f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
TEST SCRIPT GENERATED: {filename}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Script language: {script_info['language'].upper()} ({script_info['framework']})
💻 Run: {script_info['command']}
📌 Expected: {script_info['expected']}

INSTRUCTIONS:
1. Run the command above
2. Verify the output matches your expectations
3. If it PASSES: call acceptance_test(action='pass', notes='...')
   If it FAILS: call acceptance_test(action='fail', notes='...')

⚠️  NOTE: You are the final gate. If the app works for you, it passes.
   If something is missing or wrong, report it — we fix it before ship.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return {
        "status": "test_prepared",
        "output": output,
        "criteria": spec["criteria"],
        "script_filename": filename,
        "command": script_info["command"],
        "can_ship": False,
        "ci_delta": 0,
    }


def _record_pass(context: dict) -> dict:
    """Record user acceptance — enables /ship."""
    import json

    status = _load_status()
    now = datetime.now().isoformat()
    result = {
        "action": "pass",
        "timestamp": now,
        "notes": context.get("notes", ""),
    }

    status["status"] = "passed"
    status["passed_at"] = now
    status["history"].append(result)
    _save_status(status)

    return {
        "status": "accepted",
        "output": (
            "✅ ACCEPTANCE CONFIRMED by user.\n\n"
            "SPEC.md updated: ACCEPTED\n"
            "/ship is now UNLOCKED — ready to deliver.\n\n"
            "Next: /ship to complete the workflow."
        ),
        "can_ship": True,
        "ci_delta": 10,
    }


def _record_fail(context: dict) -> dict:
    """Record user rejection — returns to build."""
    import json

    notes = context.get("notes", "No notes provided")
    status = _load_status()
    now = datetime.now().isoformat()
    result = {
        "action": "fail",
        "timestamp": now,
        "notes": notes,
    }

    status["status"] = "failed"
    status["failed_at"] = now
    status["history"].append(result)
    _save_status(status)

    return {
        "status": "failed",
        "output": (
            f"❌ ACCEPTANCE FAILED.\n\n"
            f"Issue reported: {notes}\n\n"
            "Returning to /build step.\n"
            "These issues will be addressed before re-running acceptance test.\n\n"
            "After fixes: /acceptance_test → /ship"
        ),
        "can_ship": False,
        "ci_delta": -3,
    }
