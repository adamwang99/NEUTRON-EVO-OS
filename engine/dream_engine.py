"""
NEUTRON-EVO-OS: Dream Engine — Memory 2.0 Core
Implements Pruning (delete noise) and Distillation (compress logs into Cookbooks).
"""
from __future__ import annotations

import json
import os
import re
import shutil
import threading
from pathlib import Path
from datetime import datetime, timedelta

from engine.smart_observer import SilentObserver

NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", Path(__file__).parent.parent))
MEMORY_DIR = NEUTRON_ROOT / "memory"
ARCHIVED_DIR = MEMORY_DIR / "archived"
COOKBOOKS_DIR = MEMORY_DIR / "cookbooks"
NOISE_THRESHOLD_DAYS = 3   # days old before archiving
ARCHIVED_RETENTION_DAYS = 7  # max age for archived files

# Re-entrancy guard: prevents concurrent dream cycles
_dream_running = threading.Event()

# Sentinel file — if this file exists, observer should NOT restart dream cycle
# Prevents re-trigger after the cycle itself creates files
_DREAM_SENTINEL = MEMORY_DIR / ".dream_active"


def dream_cycle(json_output: bool = True) -> dict | str:
    """
    Execute a full Dream Cycle:
    1. Archive today's logs to /memory/archived/
    2. Prune noise (files not referenced in N days)
    3. Distill remaining logs into Cookbooks
    4. Cap archived/ retention (max age or max count)

    Args:
        json_output: if True (default), returns a JSON string (for CLI/print output).
                     if False, returns a dict (for programmatic use).

    Returns: dict, or JSON string if json_output=True.

    Note: Does NOT restart the observer — observer lifecycle is managed externally
    by make live or engine skill observer_start/observer_stop.
    """
    if _dream_running.is_set():
        result = {"status": "skipped", "reason": "already running"}
        return json.dumps(result) if json_output else result

    _dream_running.set()
    try:
        # Write sentinel BEFORE doing work — prevents observer from re-triggering
        _DREAM_SENTINEL.write_text(datetime.now().isoformat())
        result = _dream_cycle_inner()
        return json.dumps(result) if json_output else result
    finally:
        _dream_running.clear()
        # Remove sentinel AFTER work is done — observer can now safely trigger
        try:
            _DREAM_SENTINEL.unlink(missing_ok=True)
        except Exception:
            pass


def _dream_cycle_inner() -> dict:
    """Inner dream cycle logic (called within re-entrancy guard)."""
    # Ensure dirs exist
    ARCHIVED_DIR.mkdir(exist_ok=True)
    COOKBOOKS_DIR.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    now = datetime.now()

    # --- Archive Phase ---
    # Only archive files at top level of memory/ — never subdirectories.
    # Filter out subdirectory entries explicitly.
    archived_count = 0
    archived_files = []
    for log in MEMORY_DIR.iterdir():
        if not (log.is_file() and log.suffix == ".md"):
            continue
        # Skip sentinel file
        if log.name.startswith(".dream_active"):
            continue
        dest = ARCHIVED_DIR / f"{log.stem}_{timestamp}{log.suffix}"
        shutil.copy2(log, dest)
        archived_files.append(log.name)
        archived_count += 1

    # --- Prune Phase (old .tmp/.cache files only) ---
    cutoff = now - timedelta(days=NOISE_THRESHOLD_DAYS)
    pruned_files = []
    for item in list(MEMORY_DIR.iterdir()) + list(ARCHIVED_DIR.iterdir()):
        if item.name in ("archived", "cookbooks", ".dream_active"):
            continue
        if item.is_file() and item.suffix in (".tmp", ".cache"):
            mtime = datetime.fromtimestamp(item.stat().st_mtime)
            if mtime < cutoff:
                item.unlink()
                pruned_files.append(item.name)

    # --- Archive Retention Cap ---
    # Cap archived/ to ARCHIVED_RETENTION_DAYS (default 7 days).
    # Sort by mtime, delete oldest beyond threshold.
    archived_cutoff = now - timedelta(days=ARCHIVED_RETENTION_DAYS)
    deleted_retention = 0
    for archived_file in sorted(ARCHIVED_DIR.iterdir(), key=lambda f: f.stat().st_mtime):
        mtime = datetime.fromtimestamp(archived_file.stat().st_mtime)
        if mtime < archived_cutoff:
            archived_file.unlink()
            deleted_retention += 1

    # --- Distill Phase (top-level .md only) ---
    distilled = []
    for log in MEMORY_DIR.iterdir():
        if not (log.is_file() and log.suffix == ".md"):
            continue
        if log.name.startswith(".dream_active"):
            continue
        result = distill_log(str(log))
        if result.get("status") == "distilled":
            distilled.append(result["cookbook"])

    # --- Stop observer during dream cycle (avoid re-trigger) ---
    # Pass NEUTRON_ROOT so stop() only affects THIS project, not sibling observers
    try:
        SilentObserver.stop(str(NEUTRON_ROOT))
    except Exception:
        pass

    return {
        "status": "dream_complete",
        "timestamp": timestamp,
        "archived": archived_count,
        "archived_files": archived_files,
        "pruned": len(pruned_files),
        "pruned_files": pruned_files,
        "distilled": len(distilled),
        "cookbooks": distilled,
        "retention_deleted": deleted_retention,
    }


def distill_log(log_path: str) -> dict:
    """
    Compress a log into a Cookbook summary with actionable insights.
    Extracts patterns, errors, decisions, and CI scores from session logs.
    No LLM needed — pure heuristic analysis.

    Returns: {status, cookbook, entries_extracted}
    """
    path = Path(log_path)
    if not path.exists():
        return {"status": "error", "message": f"Log not found: {log_path}"}

    content = path.read_text()
    lines = [l.strip() for l in content.splitlines() if l.strip()]

    # ── Extract structured data ───────────────────────────────────────────
    # CI deltas
    ci_deltas = []
    for l in lines:
        m = re.search(r"ci delta:\s*([+-]?\d+)", l, re.IGNORECASE)
        if m:
            ci_deltas.append(int(m.group(1)))

    # Errors
    error_lines = [l for l in lines if "error" in l.lower() or "fail" in l.lower()]
    # Ok/completed lines
    ok_lines = [l for l in lines if l.lower().startswith("outcome:") and "ok" in l.lower()]
    # Decisions
    decision_lines = [l for l in lines if "decision:" in l.lower()]
    # Checkpoints (milestones)
    checkpoint_lines = [l for l in lines if l.startswith("## [")]
    # Skills invoked
    skill_invocations = re.findall(r"skill:\s*(\w+)", " ".join(lines), re.IGNORECASE)

    # Repeated error patterns (same error ≥ 2x → flagged)
    error_counts: dict[str, int] = {}
    for l in error_lines:
        # Normalize: strip timestamps and paths
        normalized = re.sub(r"\d{4}-\d{2}-\d{2}", "[DATE]", l)
        normalized = re.sub(r"/[\w/\.-]+", "[PATH]", normalized)
        normalized = re.sub(r"[a-f0-9]{6,}", "[HASH]", normalized)
        error_counts[normalized] = error_counts.get(normalized, 0) + 1
    repeated_errors = {k: v for k, v in error_counts.items() if v >= 2}

    # ── Build cookbook ─────────────────────────────────────────────────────
    cookbook_name = f"{path.stem}_cookbook.md"
    cookbook_path = COOKBOOKS_DIR / cookbook_name

    total_ci = sum(ci_deltas)
    net_ci = sum(ci_deltas)
    ci_label = "positive" if net_ci >= 0 else "concerning"

    cookbook_content = [
        f"# Cookbook: {path.stem}",
        "",
        f"> Distilled on {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"> ∫f(t)dt — Functional Credibility Over Institutional Inertia",
        "",
        f"## Summary",
        f"- Sessions log: {path.name}",
        f"- Checkpoints recorded: {len(checkpoint_lines)}",
        f"- Skills invoked: {len(skill_invocations)}",
        f"- CI delta total: {total_ci:+.0f} ({ci_label})",
        f"- Outcomes: {len(ok_lines)} ok / {len(error_lines)} errors",
        f"- Decisions recorded: {len(decision_lines)}",
        "",
    ]

    if repeated_errors:
        cookbook_content += [
            f"## ⚠️  Repeated Errors ({len(repeated_errors)} pattern(s))",
            "These errors appeared 2+ times — consider adding to LEARNED.md:",
            "",
        ]
        for err, count in sorted(repeated_errors.items(), key=lambda x: -x[1]):
            cookbook_content.append(f"- [{count}x] {err[:100]}")
        cookbook_content.append("")

    if decision_lines:
        cookbook_content += [
            f"## 📌 Decisions ({len(decision_lines)})",
            "",
        ]
        for d in decision_lines[:10]:
            cookbook_content.append(f"- {d[:120]}")
        cookbook_content.append("")

    if error_lines:
        cookbook_content += [
            f"## Errors Encountered ({len(error_lines)})",
            "",
        ]
        for e in error_lines[:10]:
            cookbook_content.append(f"- {e[:120]}")
        cookbook_content.append("")

    cookbook_content += [
        f"## Key Milestones ({len(checkpoint_lines)})",
        "",
    ]
    for c in checkpoint_lines[:20]:
        cookbook_content.append(f"- {c[:120]}")
    cookbook_content.append("")

    if skill_invocations:
        # Count skill usage
        skill_counts: dict[str, int] = {}
        for s in skill_invocations:
            skill_counts[s.lower()] = skill_counts.get(s.lower(), 0) + 1
        cookbook_content += [
            f"## 🔧 Skills Used ({len(skill_invocations)} invocations)",
            "",
        ]
        for s, c in sorted(skill_counts.items(), key=lambda x: -x[1]):
            cookbook_content.append(f"- {s}: {c}x")
        cookbook_content.append("")

    cookbook_content += [
        f"## CI Breakdown",
        f"- Total CI delta: {total_ci:+.0f}",
        f"- Actions: {len(ci_deltas)}",
        f"- Avg per action: {total_ci/len(ci_deltas):.1f}" if ci_deltas else "- No CI data",
        "",
        "---",
        "*Auto-generated by NEUTRON Dream Cycle. Do not edit — archive instead.*",
    ]

    cookbook_path.write_text("\n".join(cookbook_content))

    return {
        "status": "distilled",
        "cookbook": str(cookbook_path),
        "entries_extracted": len(checkpoint_lines) + len(error_lines) + len(decision_lines),
        "repeated_errors": len(repeated_errors),
        "net_ci": net_ci,
    }


def archive_user_data(file_path: str) -> dict:
    """
    Safely archive user data to /memory/archived/.
    Returns: {status, archived_to}
    """
    path = Path(file_path)
    if not path.exists():
        return {"status": "error", "message": f"File not found: {file_path}"}

    ARCHIVED_DIR.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived_name = f"{path.stem}_{timestamp}{path.suffix}"
    archived_path = ARCHIVED_DIR / archived_name

    shutil.copy2(path, archived_path)

    return {
        "status": "archived",
        "archived_to": str(archived_path),
        "original": str(path),
    }
