"""
NEUTRON EVO OS — Regression Guard
Prevents edits from breaking already-working features.

Architecture:
  1. SNAPSHOT  — Before edit: record golden outputs of critical skills
  2. SMOKE     — After edit: run critical skills with known inputs
  3. COMPARE   — Diff current vs golden outputs
  4. ALERT/BLOCK — If regression detected, log + optional block

Critical paths protected:
  - engine/*    : core modules (skill_execution, skill_registry, expert_skill_router, etc.)
  - skills/core/*/logic/__init__.py : all skill logic
  - hooks/*     : session hooks

Triggered by: PreToolUse hook → calls regression_check() on every file edit.
Can also run standalone: neutron regress
"""
from __future__ import annotations

import datetime
import filelock
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

from engine._atomic import atomic_write

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
GUARD_DIR = NEUTRON_ROOT / "memory" / ".regression"
GUARD_MANIFEST = GUARD_DIR / "manifest.json"    # golden outputs + metadata
GUARD_LOCK = GUARD_DIR / "manifest.lock"
GUARD_LOG = GUARD_DIR / "regression_log.md"

# Critical skills + their test inputs (must be fast, deterministic)
# NOTE: Exclude stateful skills (memory, checkpoint) — their outputs vary per call.
# Only test deterministic skills where status + ci_delta are stable.
SMOKE_TESTS = [
    ("context", "audit context", {"action": "audit"}),
    ("engine", "audit", {"action": "audit"}),
]

# Modules that MUST import without error
CRITICAL_IMPORTS = [
    "engine.skill_execution",
    "engine.skill_registry",
    "engine.expert_skill_router",
    "engine.context_snapshot",
    "engine.learned_skill_builder",
    "engine.rating",
    "engine.auto_confirm",
    "engine.dream_engine",
    "engine.smart_observer",
]


# ── Manifest Management ────────────────────────────────────────────────────────

def _load_manifest() -> dict:
    """Load regression manifest (golden outputs + metadata)."""
    GUARD_DIR.mkdir(parents=True, exist_ok=True)
    if GUARD_MANIFEST.exists():
        try:
            return json.loads(GUARD_MANIFEST.read_text())
        except Exception:
            pass
    return {"version": 1, "smoke": {}, "imports": {}, "snapshots": {}, "last_run": None}


def _save_manifest(data: dict):
    """Save manifest atomically with filelock."""
    import filelock
    lock = filelock.FileLock(str(GUARD_LOCK), timeout=10)
    with lock:
        atomic_write(GUARD_MANIFEST, json.dumps(data, indent=2, ensure_ascii=False))


# ── Output Fingerprinting ──────────────────────────────────────────────────────

def _fingerprint(output: str | dict, result: dict) -> dict:
    """Create a stable fingerprint of skill output for comparison."""
    # Normalize: output may be str or dict
    if isinstance(output, dict):
        output_str = json.dumps(output, sort_keys=True, ensure_ascii=False)
    else:
        output_str = str(output)
    sig = hashlib.sha256(output_str.encode()).hexdigest()[:12]
    return {
        "sig": sig,
        "len": len(output),
        "status": result.get("status"),
        "ci_delta": result.get("ci_delta"),
        "timestamp": datetime.datetime.now().isoformat(),
    }


# ── Core: Snapshot Golden Outputs ──────────────────────────────────────────────

def snapshot() -> dict:
    """
    Record current golden outputs of all smoke tests.
    Run once per stable session to establish baseline.

    Usage:
      regression_guard.snapshot()   # establish baseline
      regression_guard.snapshot()   # refresh after intentional improvements
    """
    manifest = _load_manifest()
    new_smoke = {}
    new_imports = {}
    snapshot_time = datetime.datetime.now().isoformat()

    # ── Snapshot skill smoke tests ────────────────────────────────────────────
    for skill_name, task, ctx in SMOKE_TESTS:
        key = f"skill:{skill_name}"
        try:
            # Fresh import per skill to catch module-level crashes
            from engine import skill_execution
            result = skill_execution.run(skill_name, task, ctx)
            output = result.get("output", "")
            fp = _fingerprint(output, result)
            fp["snapshot_at"] = snapshot_time
            new_smoke[key] = fp
            new_smoke[f"{key}:output"] = output
        except Exception as e:
            new_smoke[key] = {
                "error": str(e),
                "snapshot_at": snapshot_time,
            }

    # ── Snapshot critical imports ───────────────────────────────────────────────
    for mod in CRITICAL_IMPORTS:
        key = f"import:{mod}"
        try:
            __import__(mod)
            new_imports[key] = {
                "ok": True,
                "snapshot_at": snapshot_time,
            }
        except Exception as e:
            new_imports[key] = {
                "ok": False,
                "error": str(e),
                "snapshot_at": snapshot_time,
            }

    manifest["smoke"] = new_smoke
    manifest["imports"] = new_imports
    manifest["last_snapshot"] = snapshot_time
    _save_manifest(manifest)

    return {
        "status": "snapshot_saved",
        "smoke_count": len(new_smoke),
        "import_count": len(new_imports),
        "skills_ok": sum(1 for v in new_smoke.values() if "error" not in v),
        "imports_ok": sum(1 for v in new_imports.values() if v.get("ok")),
    }


# ── Core: Smoke Test (run after edit) ─────────────────────────────────────────

def _run_skill_smoke(skill_name: str, task: str, ctx: dict) -> dict:
    """Run a single skill smoke test and return result."""
    try:
        from engine import skill_execution
        result = skill_execution.run(skill_name, task, ctx)
        return {"ok": True, "result": result}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _run_import_check(mod: str) -> dict:
    """Check a single module imports cleanly."""
    try:
        __import__(mod)
        return {"ok": True}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def smoke_test() -> dict:
    """
    Run smoke tests WITHOUT comparing to golden outputs.
    Fast check: did any critical skill crash or throw an exception?
    """
    results = {"skills": {}, "imports": {}}
    all_ok = True

    for skill_name, task, ctx in SMOKE_TESTS:
        key = f"skill:{skill_name}"
        r = _run_skill_smoke(skill_name, task, ctx)
        results["skills"][key] = r
        if not r["ok"]:
            all_ok = False

    for mod in CRITICAL_IMPORTS:
        key = f"import:{mod}"
        r = _run_import_check(mod)
        results["imports"][key] = r
        if not r["ok"]:
            all_ok = False

    return {
        "status": "ok" if all_ok else "smoke_failed",
        "skills_ok": sum(1 for v in results["skills"].values() if v["ok"]),
        "skills_total": len(SMOKE_TESTS),
        "imports_ok": sum(1 for v in results["imports"].values() if v["ok"]),
        "imports_total": len(CRITICAL_IMPORTS),
        "details": results,
    }


# ── Core: Regression Check ─────────────────────────────────────────────────────

def check(changed_files: list[str] = None, changed_modules: list[str] = None) -> dict:
    """
    Run full regression check after edits.

    Args:
        changed_files: list of absolute file paths that were modified
        changed_modules: list of module prefixes that were modified
                        (e.g. ["engine.skill_execution", "skills.core.memory"])

    Returns:
        {status, regressions: [], warnings: [], ok: bool}

    status values:
      clean       : no regressions detected
      regressions  : regressions found — review required
      no_baseline : no golden snapshot exists — run snapshot() first
      error       : check itself failed (e.g. import error in guard)
    """
    if changed_files:
        changed_files = [str(Path(f).resolve()) for f in changed_files]
    if changed_modules:
        changed_modules = list(changed_modules)
    else:
        # Infer changed modules from changed_files paths
        changed_modules = _infer_modules(changed_files or [])

    manifest = _load_manifest()
    if not manifest.get("smoke") or not manifest.get("imports"):
        return {
            "status": "no_baseline",
            "output": (
                "No regression baseline found.\n"
                "Run: regression_guard.snapshot() to establish golden outputs.\n"
                "Then edits will be checked against this baseline."
            ),
            "ok": False,
            "regressions": [],
        }

    regressions = []
    warnings = []
    snapshot_time = manifest.get("last_snapshot", "unknown")

    # ── 1. Skill smoke tests ───────────────────────────────────────────────────
    for skill_name, task, ctx in SMOKE_TESTS:
        key = f"skill:{skill_name}"

        # Only check if a related module was changed
        if changed_modules and not _module_affected(skill_name, changed_modules):
            continue

        current = _run_skill_smoke(skill_name, task, ctx)
        golden = manifest["smoke"].get(key, {})
        golden_fp = manifest["smoke"].get(f"{key}:output", "")

        if not current["ok"]:
            # Crash: skill throws exception
            regressions.append({
                "type": "crash",
                "target": key,
                "module": skill_name,
                "detail": current["error"],
                "severity": "HIGH",
                "fix": f"Fix exception in {skill_name} skill logic",
            })
            continue

        # Fingerprint comparison
        result = current["result"]
        output = result.get("output", "")
        fp = _fingerprint(output, result)

        if "error" in golden and "error" not in fp:
            # This is an improvement, not a regression — skip
            pass
        elif golden.get("sig") and fp["sig"] != golden["sig"]:
            # Output changed — could be improvement OR regression
            if fp["status"] != golden.get("status"):
                # Status changed — flag as regression
                regressions.append({
                    "type": "status_change",
                    "target": key,
                    "module": skill_name,
                    "golden_status": golden.get("status"),
                    "current_status": fp["status"],
                    "golden_ci": golden.get("ci_delta"),
                    "current_ci": fp.get("ci_delta"),
                    "severity": "MEDIUM",
                    "fix": f"{skill_name} skill returned unexpected status after edit. "
                           f"Golden: {golden.get('status')} → Current: {fp['status']}",
                })
            elif fp["ci_delta"] != golden.get("ci_delta"):
                # CI delta changed — flag as warning
                warnings.append({
                    "type": "ci_delta_change",
                    "target": key,
                    "module": skill_name,
                    "golden_ci": golden.get("ci_delta"),
                    "current_ci": fp.get("ci_delta"),
                    "severity": "LOW",
                })
            else:
                # Output changed but status + ci_delta same — informational only
                warnings.append({
                    "type": "output_diff",
                    "target": key,
                    "module": skill_name,
                    "golden_len": golden.get("len", 0),
                    "current_len": fp["len"],
                    "severity": "INFO",
                })

    # ── 2. Import checks ──────────────────────────────────────────────────────
    for mod in CRITICAL_IMPORTS:
        key = f"import:{mod}"

        if changed_modules and not _module_affected(mod, changed_modules):
            continue

        current = _run_import_check(mod)
        golden = manifest["imports"].get(key, {})

        if not current["ok"] and golden.get("ok"):
            regressions.append({
                "type": "import_error",
                "target": key,
                "module": mod,
                "detail": current["error"],
                "severity": "HIGH",
                "fix": f"Fix import error in {mod}: {current['error']}",
            })
        elif not current["ok"] and not golden.get("ok"):
            # Already broken before — not a new regression
            pass

    # ── 3. Log regression results ─────────────────────────────────────────────
    _log_check(changed_modules, regressions, warnings, snapshot_time)

    if regressions:
        return {
            "status": "regressions",
            "ok": False,
            "regressions": regressions,
            "warnings": warnings,
            "output": _format_regression_output(regressions, warnings),
            "snapshot_at": snapshot_time,
            "changed_modules": changed_modules,
        }
    if warnings:
        return {
            "status": "warnings",
            "ok": True,
            "regressions": [],
            "warnings": warnings,
            "output": _format_warning_output(warnings),
            "snapshot_at": snapshot_time,
            "changed_modules": changed_modules,
        }
    return {
        "status": "clean",
        "ok": True,
        "regressions": [],
        "warnings": [],
        "output": "No regressions detected. All critical skills healthy.",
        "snapshot_at": snapshot_time,
        "changed_modules": changed_modules,
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _infer_modules(changed_files: list[str]) -> list[str]:
    """Infer module prefixes from changed file paths."""
    modules = set()
    for f in changed_files:
        p = Path(f)
        try:
            p.relative_to(NEUTRON_ROOT)
        except ValueError:
            continue

        rel = str(p.relative_to(NEUTRON_ROOT))
        if rel.startswith("engine/"):
            modules.add(f"engine.{p.stem}")
        elif rel.startswith("skills/core/"):
            parts = rel.split("/")
            if len(parts) >= 3:
                modules.add(f"skills.core.{parts[2]}")
        elif rel.startswith("skills/"):
            modules.add("skills")
        elif rel.startswith("mcp_server/"):
            modules.add("mcp_server")
        elif rel.startswith("hooks/"):
            modules.add("hooks")
    return list(modules)


def _module_affected(target: str, changed_modules: list[str]) -> bool:
    """True if the target module/skill is affected by the changed modules."""
    for changed in changed_modules:
        if target.startswith(changed):
            return True
        # Partial match: "engine.skill_execution" affected by "engine"
        if "." in changed and target.startswith(changed.split(".")[0]):
            return True
    return True  # Default: check all if no modules specified


def _log_check(changed_modules: list[str], regressions: list, warnings: list,
                snapshot_time: str):
    """Append regression check result to the log file."""
    GUARD_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    lines = [
        f"\n## [{ts}] Regression Check",
        f"  Changed: {', '.join(changed_modules) or 'unknown'}",
        f"  Snapshot: {snapshot_time}",
        f"  Regressions: {len(regressions)}",
        f"  Warnings: {len(warnings)}",
    ]
    for r in regressions:
        lines.append(f"  🔴 {r['type']} in {r['target']}: {r['detail'] or r.get('fix','')}")
    for w in warnings:
        lines.append(f"  🟡 {w['type']} in {w['target']}: {w.get('detail','')}")

    lock = filelock.FileLock(str(GUARD_LOCK), timeout=5)
    try:
        with lock:
            content = GUARD_LOG.read_text() if GUARD_LOG.exists() else ""
            GUARD_LOG.write_text(content + "\n".join(lines) + "\n")
    except Exception:
        pass  # Best-effort logging


def _format_regression_output(regressions: list, warnings: list) -> str:
    lines = [
        f"⚠️  {len(regressions)} REGRESSION(S) DETECTED — REVIEW REQUIRED",
        "─" * 52,
    ]
    for i, r in enumerate(regressions, 1):
        lines.append(f"  {i}. [{r['severity']}] {r['type']} in {r['target']}")
        if r.get("detail"):
            lines.append(f"     Error: {r['detail'][:120]}")
        if r.get("fix"):
            lines.append(f"     Fix:   {r['fix']}")
    if warnings:
        lines.append(f"\n  {len(warnings)} warning(s):")
        for w in warnings:
            lines.append(f"  - {w['type']} in {w['target']}: ci_delta {w.get('golden_ci')} → {w.get('current_ci')}")
    lines.append("")
    lines.append("  Options:")
    lines.append("    neutron regress --snapshot   # refresh golden baseline")
    lines.append("    neutron regress --force     # proceed despite regressions")
    return "\n".join(lines)


def _format_warning_output(warnings: list) -> str:
    lines = [f"🟡 {len(warnings)} warning(s) — not blocking:"]
    for w in warnings:
        lines.append(f"  - {w['type']} in {w['target']}")
    return "\n".join(lines)


# ── Public API ─────────────────────────────────────────────────────────────────

def regression_check(changed_files: list[str] = None) -> dict:
    """
    Main entry point for PreToolUse hook.
    Call with list of files that were just modified.
    """
    return check(changed_files=changed_files)


# ── CLI Integration ─────────────────────────────────────────────────────────────

def run_cli(args: list[str] = None) -> dict:
    """
    CLI: neutron regress [--snapshot] [--check] [--force]
    """
    import argparse
    parser = argparse.ArgumentParser(description="NEUTRON Regression Guard")
    parser.add_argument("--snapshot", action="store_true", help="Record golden snapshot")
    parser.add_argument("--check", action="store_true", help="Run regression check")
    parser.add_argument("--force", action="store_true", help="Proceed despite regressions")
    parser.add_argument("--files", nargs="*", help="Changed files (auto-detected if omitted)")
    parsed = parser.parse_args(args or [])

    if parsed.snapshot:
        return snapshot()

    if parsed.check or parsed.files:
        result = check(changed_files=parsed.files)
        if not result["ok"] and not parsed.force:
            print(result["output"], file=sys.stderr)
            sys.exit(1)
        return result

    # Default: run smoke test
    return smoke_test()


if __name__ == "__main__":
    import sys as _sys
    result = run_cli(_sys.argv[1:])
    print(json.dumps(result, indent=2, default=str))
