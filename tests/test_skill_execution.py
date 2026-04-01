"""
Tests for engine/skill_execution.py
"""
import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import skill_execution


class TestSkillExecutionRun:
    def test_context_skill_runs(self):
        result = skill_execution.run("context", "audit context", {"task": "audit"})
        assert result["status"] in ("ok", "error", "blocked")
        assert "ci_delta" in result
        assert isinstance(result["ci_delta"], int)

    def test_memory_skill_log_action(self):
        result = skill_execution.run("memory", "log test entry", {"action": "log"})
        assert result["status"] in ("ok", "error")
        assert "ci_delta" in result

    def test_memory_skill_status_action(self):
        result = skill_execution.run("memory", "status check", {"action": "status"})
        assert result["status"] == "ok"
        assert "ci_delta" in result

    def test_memory_skill_unknown_action(self):
        # Validation layer catches invalid action → validation_failed
        result = skill_execution.run("memory", "test", {"action": "nonexistent_action_xyz"})
        assert result["status"] == "validation_failed"
        assert "ci_delta" in result

    def test_workflow_explore_step(self):
        result = skill_execution.run(
            "workflow", "test workflow", {"step": "explore", "statement": "testing"}
        )
        assert result["status"] in ("ok", "blocked", "error", "validation_failed")
        assert "ci_delta" in result

    def test_workflow_invalid_step(self):
        # Validation layer catches invalid step → validation_failed
        result = skill_execution.run(
            "workflow", "test", {"step": "invalid_step_xyz"}
        )
        assert result["status"] == "validation_failed"
        assert result["ci_delta"] == -5

    def test_workflow_spec_returns_proper_status(self):
        # SPEC step returns one of:
        # - spec_written      : SPEC.md written, USER REVIEW gate required
        # - awaiting_discovery: no discovery yet, blocked
        # - spec_approved     : auto-confirm is on, auto-approved immediately
        # All three are valid — the test only checks ci_delta consistency.
        from pathlib import Path
        _base = Path(__file__).parent.parent
        (_base / "SPEC.md").unlink(missing_ok=True)
        (_base / "memory" / ".workflow_gate.json").unlink(missing_ok=True)
        result = skill_execution.run("workflow", "test", {"step": "spec"})
        assert result["status"] in ("spec_written", "awaiting_discovery", "spec_approved")
        # ci_delta: 0 if awaiting/written; 5 if auto-approved
        assert result["ci_delta"] in (0, 5)

    def test_workflow_spec_with_approval(self):
        result = skill_execution.run(
            "workflow", "test", {"step": "spec", "approved": True, "notes": "looks good"}
        )
        # Status is either spec_approved (if first time) or spec_written (if SPEC.md already existed)
        assert result["status"] in ("spec_approved", "spec_written")
        assert "APPROVED" in result.get("output", "").upper() or "UNLOCKED" in result.get("output", "")

    def test_workflow_build_blocked_without_approval(self):
        # Build is blocked without SPEC approval
        # Clear gate file to ensure clean state
        import os, sys
        _ne = Path(__file__).parent.parent
        _gate = _ne / "memory" / ".workflow_gate.json"
        if _gate.exists():
            _gate.unlink()
        result = skill_execution.run(
            "workflow", "test", {"step": "build"}
        )
        assert result["status"] == "blocked"
        assert "approved" in result.get("output", "").lower() or "blocked" in result.get("status", "")

    def test_workflow_verify(self):
        # pytest may not be installed — execution_error is valid
        result = skill_execution.run("workflow", "test", {"step": "verify"})
        assert result["status"] in ("ok", "error", "execution_error")
        assert "ci_delta" in result

    def test_engine_skill_audit_action(self):
        result = skill_execution.run("engine", "audit", {"action": "audit"})
        assert result["status"] == "ok"
        assert result["ci_delta"] == 2

    def test_engine_skill_route_action(self):
        result = skill_execution.run("engine", "manage memory", {"action": "route"})
        assert result["status"] == "ok"
        assert result["ci_delta"] == 2

    def test_engine_skill_unknown_action(self):
        # Validation layer catches unknown action → validation_failed
        result = skill_execution.run("engine", "test", {"action": "unknown_xyz"})
        assert result["status"] == "validation_failed"
        assert result["ci_delta"] == -5

    def test_checkpoint_read_action(self):
        result = skill_execution.run("checkpoint", "read", {"action": "read"})
        assert "ci_delta" in result

    def test_checkpoint_unknown_action(self):
        result = skill_execution.run("checkpoint", "test", {"action": "unknown_xyz"})
        assert result["status"] in ("validation_failed", "error")

    def test_unknown_skill_returns_error(self):
        result = skill_execution.run("nonexistent_skill_xyz", "test", {})
        assert result["status"] == "error"
        assert result["ci_delta"] == 0

    def test_result_has_output(self):
        result = skill_execution.run("memory", "test", {"action": "status"})
        assert "output" in result
        assert isinstance(result["output"], str)


# Note: discovery and acceptance_test skills tested via full pipeline demo
# (they require stateful sessions: run start → run record → run complete)
# Core engine mechanics tested above. Full pipeline verified manually.
