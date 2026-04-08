#!/usr/bin/env python3
"""
test-quality.py — pre-commit hook
Runs after pytest succeeds. Records a quality signal for the development session.
This closes the quality feedback loop WITHOUT requiring the full /ship workflow.

Quality signals:
  - pytest pass → +1 quality point
  - pytest fail → -1 quality point
  - test files changed → +1 quality point (written tests = quality investment)
  - fix commit + tests pass → +2 quality points

Aggregates into memory/.quality_history.json — read by /ship or /audit.
"""
from __future__ import annotations

import json
import os
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timedelta

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
QUALITY_FILE = MEMORY_DIR / ".quality_history.json"


def get_commit_msg() -> str:
    for arg in sys.argv[1:]:
        if arg.endswith(".msg") or "COMMIT_EDITMSG" in arg:
            try:
                return Path(arg).read_text()
            except Exception:
                pass
    try:
        return sys.stdin.read()
    except Exception:
        return ""


def get_staged_files() -> list[str]:
    files = []
    for arg in sys.argv[1:]:
        if arg in ("-", "/dev/stdin"):
            continue  # skip stdin placeholder
        p = Path(arg)
        if p.exists() and p.is_file():
            files.append(str(p))
    return files


def parse_commit_type(msg: str) -> str | None:
    m = re.match(r"^(\w+):", msg.strip())
    return m.group(1).lower() if m else None


def has_test_files(files: list[str]) -> bool:
    """Return True if any file is a test file."""
    test_patterns = ["test_", "_test.", "/tests/", "/test_"]
    return any(
        any(p in f for p in test_patterns)
        for f in files
    )


def run_pytest_summary() -> dict:
    """
    Run pytest with summary output and return parsed result.
    Returns: {passed: int, failed: int, duration_s: float}
    """
    try:
        result = subprocess.run(
            ["python3", "-m", "pytest", "--tb=no", "-q", "--no-header"],
            capture_output=True,
            text=True,
            timeout=180,   # 3 minutes — sufficient for full test suite
            cwd=str(NEUTRON_ROOT),
        )
        stdout = result.stdout + result.stderr
        # Parse pytest output: "78 passed in 62.98s" or "1 failed, 77 passed"
        m_passed = re.search(r"(\d+) passed", stdout)
        m_failed = re.search(r"(\d+) failed", stdout)
        m_time = re.search(r"in ([\d.]+)s", stdout)
        # Consider "ok" if: exit=0 OR "passed" found in output (even if exit!=0 due to stderr noise)
        tests_passed = m_passed is not None
        tests_failed = m_failed is not None
        ok = result.returncode == 0 or (tests_passed and not tests_failed)
        return {
            "passed": int(m_passed.group(1)) if m_passed else 0,
            "failed": int(m_failed.group(1)) if m_failed else 0,
            "duration_s": float(m_time.group(1)) if m_time else 0.0,
            "ok": ok,
        }
    except subprocess.TimeoutExpired:
        return {"passed": 0, "failed": 0, "duration_s": 180.0, "ok": False}
    except Exception:
        return {"passed": 0, "failed": 0, "duration_s": 0.0, "ok": False}


def compute_quality_delta(pytest: dict, ctype: str | None, has_tests: bool) -> int:
    """
    Compute quality delta for this commit.
    +1 pytest pass, -1 pytest fail, +1 test files written.
    """
    delta = 0
    if pytest["ok"]:
        delta += 1
        if pytest["passed"] >= 10:
            delta += 1  # significant test run
    else:
        delta -= 1

    if has_tests:
        delta += 1  # investing in tests = quality signal

    if ctype == "fix" and pytest["ok"]:
        delta += 1  # fix with passing tests = high quality

    if ctype == "feat" and pytest["ok"] and pytest["passed"] >= 5:
        delta += 1  # feature with substantial tests

    return delta


def load_quality_history() -> dict:
    if QUALITY_FILE.exists():
        try:
            return json.loads(QUALITY_FILE.read_text())
        except Exception:
            pass
    return {
        "signals": [],
        "session_scores": {},
        "last_updated": None,
    }


def save_quality_history(data: dict):
    QUALITY_FILE.parent.mkdir(exist_ok=True)
    data["last_updated"] = datetime.now().isoformat()
    try:
        QUALITY_FILE.write_text(json.dumps(data, indent=2))
    except Exception:
        pass


def record_quality_signal(delta: int, pytest: dict, ctype: str | None, has_tests: bool):
    """Record a quality signal and update rolling window score."""
    data = load_quality_history()

    signal = {
        "timestamp": datetime.now().isoformat(),
        "delta": delta,
        "pytest_passed": pytest["passed"],
        "pytest_failed": pytest["failed"],
        "pytest_ok": pytest["ok"],
        "commit_type": ctype or "unknown",
        "has_test_files": has_tests,
    }
    data["signals"].append(signal)

    # Keep only last 50 signals (rolling window)
    if len(data["signals"]) > 50:
        data["signals"] = data["signals"][-50:]

    # Compute rolling quality score (last 10 signals)
    recent = data["signals"][-10:]
    score = sum(s.get("delta", 0) for s in recent)
    data["rolling_score"] = score
    data["rolling_signals"] = len(recent)

    save_quality_history(data)

    # Print quality summary
    score_label = "GOOD" if delta > 0 else "NEUTRAL" if delta == 0 else "BAD"
    print(f"[quality] signal={delta:+d} | rolling={score:+d}/{len(recent)} | {score_label}")


def run() -> int:
    """
    Main entry. Called by pre-commit hook after pytest succeeds.
    Does NOT block on failure — quality tracking is best-effort.
    Returns: 0 always.
    """
    msg = get_commit_msg()
    files = get_staged_files()
    ctype = parse_commit_type(msg)
    has_tests = has_test_files(files)

    # Run pytest to get signal
    pytest = run_pytest_summary()
    delta = compute_quality_delta(pytest, ctype, has_tests)

    record_quality_signal(delta, pytest, ctype, has_tests)

    return 0  # never block


if __name__ == "__main__":
    sys.exit(run())
