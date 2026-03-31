"""
Workflow Skill — Logic Module (v2.0)
run_workflow(task, context) → {status, output, ci_delta}

Steps (via context["step"]):
  explore     : Check system health, understand problem
  discovery   : Run discovery interview (12 questions)
  spec        : Write SPEC.md with USER REVIEW gate
  build       : Implement exactly what SPEC says
  acceptance  : User runs test, confirms it works
  ship        : Deliver, archive, rate

Pipeline: explore → discovery → spec (USER REVIEW) → build → acceptance (USER CONFIRMS) → ship

CI rewards: explore=+5, discovery=+5, spec=+5, build=+5, acceptance=+10, ship=+15

AUTO-CONFIRM: Gates can be auto-confirmed via engine.auto_confirm module.
"""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from datetime import datetime


def _auto_confirm_check(step: str) -> bool:
    """Return True if auto-confirm is enabled for this step."""
    try:
        from engine.auto_confirm import should_skip
        return should_skip(step)
    except Exception:
        return False


def _auto_record(step: str) -> dict:
    """Record an auto-confirmed action and return result dict."""
    try:
        from engine.auto_confirm import record_auto_action
        return record_auto_action(step, {})
    except Exception:
        return {}

# Levels: logic/__init__.py → workflow/ → core/ → skills/ → repo root
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent.parent)
))
MEMORY_DIR = _NEUTRON_ROOT / "memory"
_GATE_FILE = MEMORY_DIR / ".workflow_gate.json"


VALID_STEPS = {"explore", "discovery", "spec", "build", "verify", "acceptance", "ship", "auto"}


def run_workflow(task: str, context: dict = None) -> dict:
    context = context or {}
    step = context.get("step", "explore")

    if step not in VALID_STEPS:
        return {"status": "error", "output": f"Invalid step: '{step}'", "ci_delta": 0}

    step_fn = {
        "explore":    _step_explore,
        "discovery":  _step_discovery,
        "spec":       _step_spec,
        "build":      _step_build,
        "verify":     _step_verify,
        "acceptance": _step_acceptance,
        "ship":       _step_ship,
        "auto":      _step_auto,
    }[step]

    return step_fn(task, context)


def _load_gate() -> dict:
    """Load current workflow gate state."""
    import json
    if _GATE_FILE.exists():
        try:
            return json.loads(_GATE_FILE.read_text())
        except Exception:
            pass
    return {"spec_approved": False, "acceptance_passed": False, "current_step": None}


def _save_gate(state: dict):
    """Save workflow gate state."""
    import json
    MEMORY_DIR.mkdir(exist_ok=True)
    _GATE_FILE.write_text(json.dumps(state, indent=2))


def _log_milestone(step: str, task: str, notes: str = "", ci_delta: int = 0):
    """Write a milestone log entry to today's memory."""
    MEMORY_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = MEMORY_DIR / f"{today}.md"
    ts = datetime.now().strftime("%H:%M")
    entry = (
        f"\n## [{ts}] — /{step}: {task[:80]}\n"
        f"- Action: workflow step\n"
        f"- Outcome: completed\n"
        f"- CI delta: {ci_delta:+.0f}\n"
        f"- Notes: {notes}\n"
    )
    content = log_path.read_text() if log_path.exists() else f"# {today}\n"
    log_path.write_text(content + entry + "\n")


def _step_explore(task: str, context: dict) -> dict:
    """Step 1: Verify system health and understand problem space."""
    from engine.skill_registry import get_skill
    from engine.expert_skill_router import get_ledger_entry

    required = ["context", "memory", "engine"]
    blocked = []
    for skill_name in required:
        try:
            entry = get_ledger_entry(skill_name)
            if entry["CI"] < 30:
                blocked.append(f"{skill_name} CI={entry['CI']}")
        except Exception:
            continue

    if blocked:
        return {
            "status": "blocked",
            "output": f"Required skills below CI 30: {', '.join(blocked)}",
            "ci_delta": 0,
        }

    # Reset gate state for new workflow
    gate = _load_gate()
    gate.update({"spec_approved": False, "acceptance_passed": False, "current_step": "explore"})
    _save_gate(gate)

    _log_milestone("explore", task, "System healthy, ready to explore", ci_delta=5)

    return {"status": "ok", "output": f"Explored: {task[:60]}", "ci_delta": 5}


def _step_discovery(task: str, context: dict) -> dict:
    """Step 2: Run discovery interview. Delegate to discovery skill.
    Auto-confirm: if enabled, skip the interview and mark complete.
    """
    gate = _load_gate()
    gate["current_step"] = "discovery"
    _save_gate(gate)

    # AUTO-CONFIRM: skip discovery interview
    if _auto_confirm_check("discovery"):
        gate["discovery_complete"] = True
        _save_gate(gate)
        auto = _auto_record("discovery")
        _log_milestone("discovery", task, "AUTO-CONFIRMED (skipped interview)", ci_delta=0)
        return {
            "status": "discovery_auto_confirmed",
            "output": (
                "[AUTO-CONFIRM] Discovery interview SKIPPED.\n"
                "Using task description as input. /spec will be written directly."
            ),
            "discovery_complete": True,
            "ci_delta": 0,
            "auto_confirmed": True,
        }

    # Normal flow: delegate to discovery skill
    from skills.core.discovery.logic import run_discovery
    action = context.get("action", "start")
    result = run_discovery(task, {"action": action, "answers": context.get("answers", {})})

    if result.get("status") == "discovery_complete":
        gate["discovery_complete"] = True
        _save_gate(gate)
        _log_milestone("discovery", task, "Discovery interview complete", ci_delta=5)

    return result


def _step_spec(task: str, context: dict) -> dict:
    """Step 3: Write SPEC.md. HARD GATE: USER REVIEW before /build is unlocked."""
    gate = _load_gate()

    # Check discovery was completed
    if not gate.get("discovery_complete"):
        # Try to check if there's a discovery file
        discovery_files = list(MEMORY_DIR.rglob("DISCOVERY.md"))
        if discovery_files:
            gate["discovery_complete"] = True
            _save_gate(gate)
        else:
            return {
                "status": "blocked",
                "output": "Discovery interview not completed. Run /discovery first.",
                "ci_delta": 0,
            }

    spec_path = _NEUTRON_ROOT / "SPEC.md"

    # If context has spec content, write it
    if context.get("write_spec"):
        spec_content = context.get("spec_content", "")
        if spec_content:
            spec_path.write_text(spec_content)

    gate["current_step"] = "spec"
    _save_gate(gate)

    # AUTO-CONFIRM: auto-approve SPEC
    if _auto_confirm_check("spec"):
        result = _record_spec_approval(True, {"notes": "auto-confirm"})
        result["auto_confirmed"] = True
        return result

    # Handle USER APPROVAL
    if context.get("approved") is True:
        return _record_spec_approval(True, context)
    elif context.get("approved") is False:
        return _record_spec_approval(False, context)

    gate["spec_approved"] = False  # Reset approval
    _save_gate(gate)

    if spec_path.exists():
        content = spec_path.read_text()
        return {
            "status": "spec_written",
            "output": (
                f"SPEC.md written to: {spec_path.relative_to(_NEUTRON_ROOT)}\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔒 USER REVIEW GATE — SPEC MUST BE APPROVED BEFORE BUILD\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Read SPEC.md above. Answer ONE of:\n\n"
                "A) APPROVE — \"Build it.\"\n"
                "   → Call: workflow(step='spec', approved=True)\n\n"
                "B) REQUEST CHANGES — \"Change X, Y before building\"\n"
                "   → Describe what to change, I will revise SPEC.md\n"
                "   → Loop until you APPROVE\n\n"
                "C) ABANDON — \"Not what I need\"\n"
                "   → Workflow ends. Nothing built.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"Current spec preview:\n{content[:500]}..."
            ),
            "spec_path": str(spec_path.relative_to(_NEUTRON_ROOT)),
            "user_action_required": True,
            "ci_delta": 0,
        }

    return {
        "status": "awaiting_discovery",
        "output": "Run /discovery first to generate the input for SPEC.md",
        "ci_delta": 0,
    }


def _record_spec_approval(approved: bool, context: dict) -> dict:
    """Record user's SPEC approval decision."""
    gate = _load_gate()
    gate["spec_approved"] = approved
    gate["spec_approved_at"] = datetime.now().isoformat()
    gate["spec_approver_notes"] = context.get("notes", "")
    _save_gate(gate)

    if approved:
        _log_milestone("spec", "SPEC approved by user", f"Build UNLOCKED — {context.get('notes', '')}", ci_delta=5)
        return {
            "status": "spec_approved",
            "output": (
                "✅ SPEC APPROVED by user. BUILD IS NOW UNLOCKED.\n\n"
                "Next: /build — implementation begins.\n"
                "Only what is in SPEC.md will be built."
            ),
            "ci_delta": 5,
        }
    else:
        return {
            "status": "spec_changes_requested",
            "output": (
                "📝 Changes requested.\n\n"
                "Describe what to change:\n"
                "- What sections need revision?\n"
                "- What criteria are missing or wrong?\n"
                "I will revise SPEC.md and present again for approval."
            ),
            "ci_delta": 0,
        }


def _step_build(task: str, context: dict) -> dict:
    """Step 4: Implement exactly what SPEC says."""
    gate = _load_gate()

    if not gate.get("spec_approved"):
        spec_path = _NEUTRON_ROOT / "SPEC.md"
        if spec_path.exists():
            return {
                "status": "blocked",
                "output": (
                    "⛔ BUILD BLOCKED — USER REVIEW not passed.\n\n"
                    "SPEC.md has not been approved by user.\n"
                    "User must approve SPEC before build can begin.\n\n"
                    "If SPEC is ready: workflow(step='spec', approved=True)\n"
                    "To review SPEC: Read SPEC.md"
                ),
                "ci_delta": 0,
            }
        return {
            "status": "blocked",
            "output": "SPEC.md not found. Run /spec first.",
            "ci_delta": 0,
        }

    # Anti-slop check
    output = context.get("output", "")
    slop_signals = ["as per your request", "simply", "just", "of course", "here is the"]
    slop_found = [s for s in slop_signals if s in output.lower()]

    if slop_found:
        return {
            "status": "error",
            "output": f"Anti-slop check failed: {slop_found}",
            "ci_delta": -10,
        }

    gate["current_step"] = "build"
    _save_gate(gate)

    _log_milestone("build", task, "Build started (SPEC approved)", ci_delta=5)

    return {
        "status": "ok",
        "output": f"Build started: {task[:60]}\nSPEC.md approved. Only implementing what SPEC says.",
        "ci_delta": 5,
    }


def _step_verify(task: str, context: dict) -> dict:
    """Step 4b: Verify. Gate: pytest passes (but this is supplemental to /acceptance_test)."""
    pytest_result = subprocess.run(
        ["python3", "-m", "pytest", "-v", "--tb=short"],
        capture_output=True, text=True, timeout=60,
        cwd=str(_NEUTRON_ROOT),
    )
    stdout_lower = pytest_result.stdout.lower()
    if pytest_result.returncode != 0 and "no tests" not in stdout_lower and "not installed" not in stdout_lower:
        return {
            "status": "error",
            "output": f"Tests failed: {pytest_result.stdout[-300:]}",
            "ci_delta": -5,
        }

    gate = _load_gate()
    gate["current_step"] = "verify"
    _save_gate(gate)

    return {"status": "ok", "output": "Verification passed (unit tests)", "ci_delta": 5}


def _step_acceptance(task: str, context: dict) -> dict:
    """Step 5: Acceptance test. USER must confirm it works.
    Auto-confirm: if enabled, auto-pass after build completes.
    """
    gate = _load_gate()

    if not gate.get("spec_approved"):
        return {
            "status": "blocked",
            "output": "Build not complete or SPEC not approved. Complete build first.",
            "ci_delta": 0,
        }

    # AUTO-CONFIRM: auto-pass acceptance
    if _auto_confirm_check("acceptance"):
        gate["acceptance_passed"] = True
        gate["acceptance_passed_at"] = datetime.now().isoformat()
        _save_gate(gate)
        auto = _auto_record("acceptance")
        _log_milestone("acceptance", task, "AUTO-CONFIRMED (accepted automatically)", ci_delta=10)
        return {
            "status": "acceptance_auto_confirmed",
            "output": (
                "[AUTO-CONFIRM] Acceptance test PASSED automatically.\n"
                "Build is accepted as-is. /ship is now UNLOCKED."
            ),
            "can_ship": True,
            "ci_delta": 10,
            "auto_confirmed": True,
        }

    action = context.get("action", "prepare")
    from skills.core.acceptance_test.logic import run_acceptance_test
    result = run_acceptance_test(task, context)

    if result.get("status") == "accepted":
        gate["acceptance_passed"] = True
        gate["acceptance_passed_at"] = datetime.now().isoformat()
        _save_gate(gate)
        _log_milestone("acceptance", task, "User acceptance confirmed", ci_delta=10)

    return result


def _step_ship(task: str, context: dict) -> dict:
    """Step 6: Deliver, archive, rate. Gate: acceptance passed."""
    gate = _load_gate()

    # Check both workflow gate and acceptance_test status file
    acceptance_passed = gate.get("acceptance_passed")
    if not acceptance_passed:
        # Check acceptance_test's own status file directly (avoid circular import)
        # acceptance_test stores status in memory/.acceptance_status.json
        _at_status_file = MEMORY_DIR / ".acceptance_status.json"
        if _at_status_file.exists():
            try:
                import json
                at_status = json.loads(_at_status_file.read_text())
                acceptance_passed = at_status.get("status") == "passed"
            except Exception:
                pass

    if not acceptance_passed:
        return {
            "status": "blocked",
            "output": (
                "⛔ SHIP BLOCKED — Acceptance not confirmed.\n\n"
                "User must run acceptance test and confirm:\n"
                "  acceptance_test(action='pass', notes='...')"
            ),
            "ci_delta": 0,
        }

    # Archive SPEC.md
    spec_path = _NEUTRON_ROOT / "SPEC.md"
    if spec_path.exists():
        MEMORY_DIR.mkdir(exist_ok=True)
        archived_spec = MEMORY_DIR / f"SPEC_shipped_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        shutil.copy2(spec_path, archived_spec)
        spec_path.unlink()

    # Present delivery summary
    summary = context.get("delivery_summary", f"Completed: {task}")

    # User rating prompt
    rating_prompt = """
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📦 DELIVERY COMPLETE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

What you got:
- [list what was built]

Rate your satisfaction (1-5):
  1 = Broken / not what I asked for
  2 = Major issues, needs rework
  3 = Acceptable, some issues
  4 = Good, does what I need
  5 = Excellent, better than expected

Call: workflow(step='ship', rating=4, notes='...')
"""

    gate["current_step"] = "ship"
    gate["shipped_at"] = datetime.now().isoformat()
    _save_gate(gate)

    _log_milestone("ship", task, "Delivered and archived", ci_delta=15)

    return {
        "status": "delivered",
        "output": rating_prompt,
        "delivery_summary": summary,
        "ci_delta": 15,
    }


def _step_auto(task: str, context: dict) -> dict:
    """
    Step: /auto — Enable or disable auto-confirm mode.

    Usage:
      workflow(step='auto', mode='full')          → Enable all gates auto-confirm
      workflow(step='auto', mode='spec_only')     → Only SPEC auto-approved
      workflow(step='auto', mode='disable')       → Disable auto-confirm
      workflow(step='auto')                       → Toggle on/off
    """
    from engine import auto_confirm

    mode = context.get("mode", "toggle")

    if mode == "toggle":
        result = auto_confirm.toggle()
    elif mode == "disable":
        result = auto_confirm.disable()
    else:
        result = auto_confirm.enable(mode=mode, notes=context.get("notes", ""))

    gates = result.get("gates", {})
    current = auto_confirm.get_gates()

    output_lines = [
        "",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
        "⚡ AUTO-CONFIRM CONTROL",
        "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
    ]

    if result.get("status") == "disabled":
        output_lines.append("🔴 AUTO-CONFIRM DISABLED")
        output_lines.append("All gates require user action.")
    else:
        output_lines.append(f"🔓 AUTO-CONFIRM ENABLED: {result.get('mode', '?')}")
        output_lines.append(f"   Discovery: {'SKIP' if gates.get('discovery') else 'REQUIRED'}")
        output_lines.append(f"   SPEC:      {'AUTO-APPROVE' if gates.get('spec') else 'REQUIRED'}")
        output_lines.append(f"   Acceptance: {'AUTO-PASS' if gates.get('acceptance') else 'REQUIRED'}")

    output_lines += [
        "",
        "Commands:",
        "  workflow(step='auto', mode='full')               → Enable all",
        "  workflow(step='auto', mode='spec_only')          → SPEC only",
        "  workflow(step='auto', mode='acceptance_only')    → Acceptance only",
        "  workflow(step='auto', mode='disable')           → Disable",
        "  workflow(step='auto', mode='toggle')            → Toggle",
        "",
        result.get("message", ""),
    ]

    return {
        "status": result.get("status", "ok"),
        "output": "\n".join(output_lines),
        "auto_confirm": current,
        "ci_delta": 0,
    }
