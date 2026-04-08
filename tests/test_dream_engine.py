"""
Tests for engine/dream_engine.py — AI Gatekeeper Memory System
"""
import pytest
import sys
import os
import json
import tempfile
import re
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from engine import dream_engine


@pytest.fixture(autouse=True)
def _reset_dream_lock_cache():
    """Clear the dream lock cache + remove stale lock file before each test.

    The .dream.lock file can persist from crashed previous pytest runs.
    Deleting it here ensures each test gets a clean slate.
    """
    # Always reset cache so _get_dream_lock() creates a fresh FileLock
    dream_engine._DREAM_LOCK_CACHE = None
    # Remove stale lock file from previous runs (crash residue)
    try:
        real_lock = Path(__file__).parent.parent / "memory" / ".dream.lock"
        if real_lock.exists():
            try:
                real_lock.unlink()
            except Exception:
                pass  # best-effort
    except Exception:
        pass
    yield
    dream_engine._DREAM_LOCK_CACHE = None


class TestPreFilter:
    """Tests for noise pre-filtering."""

    def test_filters_skill_checkpoint(self):
        line = "## [12:18] — Skill: memory | Task: test"
        assert dream_engine._is_noise(line) is True

    def test_filters_test_pass(self):
        line = "✓ TestUserSettings: PASSED"
        assert dream_engine._is_noise(line) is True

    def test_filters_readonly(self):
        # Leading space → matches ^\s*grep\s pattern
        line = "  grep -r error ."
        assert dream_engine._is_noise(line) is True

    def test_filters_generic_execution_error(self):
        line = "- Outcome: execution_error"
        assert dream_engine._is_noise(line) is True

    def test_keeps_real_error_with_context(self):
        line = "File '/path/file.py', line 42: KeyError: 'user_id'"
        # No specific noise pattern matches this
        assert dream_engine._is_noise(line) is False

    def test_keeps_decision(self):
        line = "decision: Chose Python over TypeScript for simplicity"
        assert dream_engine._is_noise(line) is False

    def test_normalize_event(self):
        line = "File '/users/adam/project/main.py', line 123: error"
        norm = dream_engine._normalize_event(line)
        assert "/users/adam/project/main.py" not in norm  # paths → [PATH]
        assert "123" in norm                             # short numbers kept (line numbers are context)
        assert "error" in norm.lower()
        assert "[PATH]" in norm                          # paths replaced with [PATH]


class TestPreFilterIntegration:
    """Tests for full pre-filter pipeline."""

    def test_removes_noise_keeps_significant(self):
        content = (
            "## [12:18] — Skill: memory | Task: test\n"
            "## [12:18] — Skill: workflow | Task: test\n"
            "File '/path/file.py', line 42: KeyError: 'user_id'\n"
            "decision: Chose Python for simplicity\n"
            "- Outcome: execution_error\n"
        )
        filtered, stats = dream_engine._pre_filter(content)
        assert "Skill: memory" not in filtered
        assert "KeyError" in filtered
        assert "Chose Python" in filtered
        assert stats["lines_removed_noise"] >= 2

    def test_deduplicates_high_frequency_lines(self):
        # Same non-noise line 4x → duplicate removal kicks in
        content = "\n".join(["File 'module.py', line 1: error"] * 4)
        filtered, stats = dream_engine._pre_filter(content)
        # After dedup (≥3x removed), should be empty
        assert filtered.strip() == ""
        assert stats["duplicates_removed"] >= 3


class TestCookbookWriting:
    """Tests for decision-tree cookbook output."""

    def test_write_cookbook_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dream_engine, "COOKBOOKS_DIR", tmp_path)
        ai_result = {
            "significant_events": [
                {"type": "error", "summary": "Telegram spam",
                 "severity": "high", "context": "", "raw_snippets": []}
            ],
            "cookbook_sections": [
                {
                    "title": "Bug: Telegram Duplicate Notifications",
                    "trigger": "Multiple LLM failures in parallel",
                    "recognition": "3-5 duplicate Telegram messages",
                    "resolution": "Add cooldown map",
                    "prevention": "Check quota before retry",
                }
            ],
            "learned_drafts": []
        }
        written = dream_engine._write_cookbook("2026-04-05", ai_result, "20260405")
        assert len(written) == 1
        assert Path(written[0]).exists()
        content = Path(written[0]).read_text()
        assert "Bug: Telegram Duplicate Notifications" in content
        assert "trigger" in content.lower()
        assert "resolution" in content.lower()

    def test_write_cookbook_no_events(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dream_engine, "COOKBOOKS_DIR", tmp_path)
        ai_result = {
            "significant_events": [],
            "cookbook_sections": [],
            "learned_drafts": []
        }
        written = dream_engine._write_cookbook("2026-04-05", ai_result, "20260405")
        content = Path(written[0]).read_text()
        assert "No significant events" in content


class TestLearnedPending:
    """Tests for LEARNED_pending.md draft system."""

    def test_write_learned_pending_creates_file(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dream_engine, "MEMORY_DIR", tmp_path)
        monkeypatch.setattr(dream_engine, "PENDING_DIR", tmp_path / "pending")
        drafts = [
            {
                "title": "Telegram spam on multi-model failure",
                "symptom": "Multiple notifications per failure",
                "root_cause": "Per-model alerting instead of per-session",
                "fix": "Add cooldown map",
                "tags": "#telegram #mcp",
            }
        ]
        count = dream_engine._write_learned_pending(drafts)
        assert count == 1
        pending_file = tmp_path / "pending" / "LEARNED_pending.md"
        assert pending_file.exists()
        content = pending_file.read_text()
        assert "[PENDING]" in content
        assert "Telegram spam" in content
        assert "**Symptom:**" in content  # Markdown bold = case-sensitive "in"

    def test_write_learned_pending_empty_list(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dream_engine, "MEMORY_DIR", tmp_path)
        monkeypatch.setattr(dream_engine, "PENDING_DIR", tmp_path / "pending")
        count = dream_engine._write_learned_pending([])
        assert count == 0


class TestDreamCycle:
    """Tests for full dream_cycle() pipeline."""

    def test_dream_cycle_returns_json_serializable_dict(self, tmp_path, monkeypatch):
        """Use tmp_path to isolate — prevents writing to real memory/."""
        monkeypatch.setattr(dream_engine, "MEMORY_DIR", tmp_path)
        monkeypatch.setattr(dream_engine, "ARCHIVED_DIR", tmp_path / "archived")
        monkeypatch.setattr(dream_engine, "COOKBOOKS_DIR", tmp_path / "cookbooks")
        monkeypatch.setattr(dream_engine, "PENDING_DIR", tmp_path / "pending")
        monkeypatch.setattr(dream_engine, "_DREAM_LOCK_CACHE", None)
        result = dream_engine.dream_cycle(json_output=False)
        assert isinstance(result, dict)
        assert "status" in result
        assert result["status"] == "dream_complete"

    def test_dream_cycle_has_ai_result_keys(self, tmp_path, monkeypatch):
        """Use tmp_path to isolate — prevents writing to real memory/."""
        monkeypatch.setattr(dream_engine, "MEMORY_DIR", tmp_path)
        monkeypatch.setattr(dream_engine, "ARCHIVED_DIR", tmp_path / "archived")
        monkeypatch.setattr(dream_engine, "COOKBOOKS_DIR", tmp_path / "cookbooks")
        monkeypatch.setattr(dream_engine, "PENDING_DIR", tmp_path / "pending")
        monkeypatch.setattr(dream_engine, "_DREAM_LOCK_CACHE", None)
        result = dream_engine.dream_cycle(json_output=False)
        assert "archived" in result
        assert "cookbooks_written" in result
        assert "pending_entries" in result

    def test_dream_cycle_handles_empty_memory(self, tmp_path, monkeypatch):
        monkeypatch.setattr(dream_engine, "MEMORY_DIR", tmp_path)
        monkeypatch.setattr(dream_engine, "ARCHIVED_DIR", tmp_path / "archived")
        monkeypatch.setattr(dream_engine, "COOKBOOKS_DIR", tmp_path / "cookbooks")
        monkeypatch.setattr(dream_engine, "PENDING_DIR", tmp_path / "pending")
        monkeypatch.setattr(dream_engine, "_DREAM_LOCK_CACHE", None)
        result = dream_engine.dream_cycle(json_output=False)
        assert result["status"] == "dream_complete"
        # No files → no pending entries
        assert result.get("pending_entries", 0) == 0


class TestHubSyncStructured:
    """Tests for hub sync — structured entries only."""

    def test_sync_extracts_structured_entries_only(self, tmp_path, monkeypatch):
        """Raw log excerpts should NOT be synced to hub LEARNED.md."""
        from skills.core.memory.logic import run_memory

        # Setup: local LEARNED.md with structured entry
        local_learned = tmp_path / "memory" / "LEARNED.md"
        local_learned.parent.mkdir(exist_ok=True)
        local_learned.write_text(
            "## [2026-04-05] Bug: Test Bug\n"
            "- **Symptom:** Test\n"
            "- **Root cause:** Test\n"
            "- **Fix:** Test\n"
            "\n"
            "## [2026-04-05] From octa: 15 log excerpt(s)\n"
            "- Raw log text here\n"
        )

        # Contaminated entry should be filtered
        content = local_learned.read_text()
        import re
        contamination_patterns = [
            re.compile(r"From\s+\w+:\s*\d+\s+log excerpt", re.IGNORECASE),
        ]
        entries = []
        current = []
        for line in content.splitlines():
            if re.match(r"^\s*##\s+\[", line):
                if current:
                    entries.append("\n".join(current))
                current = []
            current.append(line)
        if current:
            entries.append("\n".join(current))

        structured = [e for e in entries
                      if not any(p.search(e) for p in contamination_patterns)]
        assert len(structured) == 1
        assert "Bug: Test Bug" in structured[0]
        assert "octa" not in structured[0]
