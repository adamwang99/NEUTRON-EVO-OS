"""
Context Skill — Logic Module
run_context(task, context) → {status, output, missing_files, load_order_ok, context_pressure, ci_delta}

Validates that P0/P1 context files are present and not corrupted.
P0 files: SOUL.md, MANIFESTO.md (always required)
P1 files: USER.md, GOVERNANCE.md, RULES.md (always required)
P2 file:  PERFORMANCE_LEDGER.md (required for CI tracking)

Context Pressure Tracking (inspired by claude-code-ultimate-guide):
- Claude Code has ~200K token budget
- NEUTRON context overhead: ~25K tokens (system + CLAUDE.md)
- Usable: ~175K tokens
- Warning threshold: 70% of usable
- Proactive compaction: 75%
- Auto-compaction: 92% (50-70% info loss on Claude Code's auto-compact)
"""
from __future__ import annotations

import datetime
import os
from pathlib import Path

# Levels: logic/__init__.py → context/ → core/ → skills/ → repo root
NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent)
))

CONTEXT_ORDER = [
    ("P0", "SOUL.md"),
    ("P0", "MANIFESTO.md"),
    ("P1", "USER.md"),
    ("P1", "GOVERNANCE.md"),
    ("P1", "RULES.md"),
    ("P2", "PERFORMANCE_LEDGER.md"),
]

# Context budget thresholds (inspired by ultimate-guide methodology)
TOKEN_BUDGET = 200_000          # Claude Code total budget
NEUTRON_OVERHEAD = 25_000      # NEUTRON system + CLAUDE.md overhead
USABLE_BUDGET = TOKEN_BUDGET - NEUTRON_OVERHEAD
WARNING_THRESHOLD = int(USABLE_BUDGET * 0.70)    # ~122,500 tokens
COMPACTION_THRESHOLD = int(USABLE_BUDGET * 0.75)  # ~131,250 tokens
CRITICAL_THRESHOLD = int(USABLE_BUDGET * 0.85)    # ~148,750 tokens


def _estimate_context_size() -> dict:
    """
    Estimate current context size from session log.

    Uses today's memory log as a proxy:
    - Each line ≈ 80 tokens (rough average: 1 token ≈ 4 chars, 1 line ≈ 20 words)
    - Today's log captures recent conversation context
    - If 2026-04-05.md has 478K lines → ~38M tokens → CRITICAL

    Context pressure degrades precision:
    - <70%: precision normal
    - 70-75%: precision starts degrading
    - >75%: significant risk of hallucinations
    - >92%: Claude Code auto-compacts → 50-70% info loss
    """
    today = datetime.datetime.now().strftime("%Y-%m-%d")
    log_path = NEUTRON_ROOT / "memory" / f"{today}.md"

    tokens = 0
    lines = 0
    if log_path.exists():
        try:
            content = log_path.read_text(errors="ignore")
            lines = content.count("\n")
            tokens = lines * 80
        except Exception:
            pass

    pct = (tokens / USABLE_BUDGET * 100) if USABLE_BUDGET > 0 else 0

    # Also check recent memory files for historical context estimate (last 30 days only)
    # Prevents memory exhaustion on repos with years of daily logs
    memory_dir = NEUTRON_ROOT / "memory"
    total_lines = 0
    cutoff = datetime.datetime.now() - datetime.timedelta(days=30)
    for f in sorted(memory_dir.glob("????-??-??.md")):
        try:
            mtime = datetime.datetime.fromtimestamp(f.stat().st_mtime)
            if mtime < cutoff:
                continue  # skip stale logs beyond 30-day window
        except Exception:
            pass
        try:
            total_lines += f.read_text(errors="ignore").count("\n")
        except Exception:
            pass

    return {
        "today_tokens": tokens,
        "today_lines": lines,
        "total_memory_lines": total_lines,
        "pct_of_usable": round(pct, 1),
        "tokens_over_warning": tokens > WARNING_THRESHOLD,
        "tokens_over_compaction": tokens > COMPACTION_THRESHOLD,
        "tokens_critical": tokens > CRITICAL_THRESHOLD,
    }


def _get_pressure_level(pct: float) -> tuple[str, str]:
    """Get pressure level and recommendation from percentage."""
    if pct < 50:
        return "🟢 NORMAL", "Context pressure low. Normal operation."
    elif pct < 70:
        return "🟡 MODERATE", "Context pressure moderate. Precision still high."
    elif pct < 75:
        return "🟠 ELEVATED", "Approaching compaction threshold. neutron snapshot save recommended."
    elif pct < 85:
        return "🔴 HIGH", "Proactive compaction needed. Run: neutron snapshot save && neutron dream"
    else:
        return "⚫ CRITICAL", (
            "Near auto-compaction threshold (92%). Claude Code will auto-compact "
            "with 50-70% info loss. ACT NOW: neutron snapshot save"
        )


def run_context(task: str, context: dict = None) -> dict:
    context = context or {}
    action = context.get("action", "audit")

    if action == "pressure":
        return _action_pressure(context)
    if action == "size":
        return _action_size(context)
    return _action_audit(context)


def _action_audit(inner_context: dict) -> dict:
    """Default: audit P0/P1/P2 context files."""
    missing = []
    present = []

    for priority, filename in CONTEXT_ORDER:
        path = NEUTRON_ROOT / filename
        if not path.exists():
            missing.append(f"[{priority}] {filename}")
        elif path.is_file() and path.stat().st_size < 10:
            missing.append(f"[{priority}] {filename} (corrupted: too small)")
        else:
            present.append(f"[{priority}] {filename}")

    if missing:
        return {
            "status": "degraded",
            "output": f"Missing/corrupted: {', '.join(missing)}",
            "missing_files": missing,
            "load_order_ok": False,
            "ci_delta": -5,
        }
    return {
        "status": "ok",
        "output": f"All {len(present)}/{len(CONTEXT_ORDER)} context files present and valid",
        "missing_files": [],
        "load_order_ok": True,
        "ci_delta": 3,
    }


def _action_pressure(inner_context: dict) -> dict:
    """
    Analyze context pressure and recommend action.

    Based on ultimate-guide's context engineering methodology:
      <50%:  normal
      50-70%: moderate
      70-75%: elevated — proactive snapshot
      75-85%: high — must compact
      >85%:   critical — auto-compact imminent
    """
    size = _estimate_context_size()
    level, recommendation = _get_pressure_level(size["pct_of_usable"])

    output_lines = [
        "Context Pressure Analysis",
        "─" * 42,
        f"Today log:  {size['today_lines']:>10,} lines (~{size['today_tokens']:>10,} tokens)",
        f"All memory: {size['total_memory_lines']:>10,} lines total",
        f"Pressure: {level}",
        f"Usage: {size['pct_of_usable']:.1f}% of usable budget ({USABLE_BUDGET:,} tokens)",
        "",
        "Thresholds:",
        f"  Warning:    {WARNING_THRESHOLD:>10,} tokens (70%)",
        f"  Compaction: {COMPACTION_THRESHOLD:>10,} tokens (75%)",
        f"  Critical:  {CRITICAL_THRESHOLD:>10,} tokens (85%)",
        "",
        f"  {recommendation}",
    ]

    if size["tokens_critical"]:
        status = "critical"
        ci_delta = -5
    elif size["tokens_over_compaction"]:
        status = "degraded"
        ci_delta = -2
    elif size["tokens_over_warning"]:
        status = "ok"
        ci_delta = 0
    else:
        status = "ok"
        ci_delta = 3

    return {
        "status": status,
        "output": "\n".join(output_lines),
        "pressure_pct": size["pct_of_usable"],
        "level": level,
        "today_tokens": size["today_tokens"],
        "today_lines": size["today_lines"],
        "total_memory_lines": size["total_memory_lines"],
        "recommendation": recommendation,
        "compact_needed": size["tokens_over_compaction"],
        "ci_delta": ci_delta,
    }


def _action_size(inner_context: dict) -> dict:
    """Show context size breakdown by file."""
    size = _estimate_context_size()

    files = []
    memory_dir = NEUTRON_ROOT / "memory"
    for f in sorted(memory_dir.glob("????-??-??.md")):
        try:
            lines = f.read_text(errors="ignore").count("\n")
            tokens = lines * 80
            files.append((f.name, lines, tokens))
        except Exception:
            pass

    output_lines = ["Context Size Breakdown", "─" * 42]
    for name, lines, tokens in sorted(files, key=lambda x: -x[1]):
        pct = tokens / USABLE_BUDGET * 100
        bar = "█" * min(int(pct / 5), 20) + "░" * max(20 - int(pct / 5), 0)
        output_lines.append(f"  {name:20s} {lines:>10,} lines  {tokens:>10,} tokens  {bar} {pct:.1f}%")

    return {
        "status": "ok",
        "output": "\n".join(output_lines),
        "files": [{"name": f, "lines": l, "tokens": t} for f, l, t in files],
        "today_tokens": size["today_tokens"],
        "today_lines": size["today_lines"],
        "ci_delta": 0,
    }
