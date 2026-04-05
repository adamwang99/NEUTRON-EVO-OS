#!/usr/bin/env python3
"""
NEUTRON EVO OS — CLI
Usage: neutron [command] [args...]

Commands:
  neutron run <task>        Run a task through the full pipeline
  neutron discover <idea>    Run discovery interview
  neutron spec [task]      Write SPEC.md (USER REVIEW gate)
  neutron build [task]     Build implementation
  neutron verify [task]    Run verification
  neutron accept [task]    Run acceptance test
  neutron ship [task]     Ship delivery

  neutron auto [mode]      Auto-confirm: full|spec_only|acceptance_only|disable|toggle
  neutron checkpoint       Write session checkpoint
  neutron status           System status + health
  neutron audit           Full CI audit

  neutron memory [action]  Memory ops: log|archive|search|dream|status
  neutron route <task>    Route task to skill
  neutron log             Show today's memory log
  neutron decisions       Show recent user decisions

Examples:
  neutron discover "Build a trading bot"
  neutron auto full       # Skip all gates
  neutron auto spec_only  # Only skip SPEC review
  neutron status
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
import os
from datetime import datetime, timedelta
from pathlib import Path

# Ensure NEUTRON_ROOT is set and repo root in path
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent)
))
sys.path.insert(0, str(_NEUTRON_ROOT))

from engine import skill_execution
from engine.expert_skill_router import route_task, audit as engine_audit
from engine import auto_confirm
from engine.rating import summarize as rating_summarize
from engine.user_decisions import summarize as decisions_summarize
from engine import __version__ as NEUTRON_VERSION
from engine.platform_sync import get_platform_status, format_sync_results


# ─── Formatters ────────────────────────────────────────────────────────────────

def _header(text: str) -> str:
    return f"\n{'='*60}\n{text}\n{'='*60}"


def _ok(text: str) -> str:
    return f"✅ {text}"


def _err(text: str) -> str:
    return f"❌ {text}"


def _info(text: str) -> str:
    return f"ℹ️  {text}"


def _warn(text: str) -> str:
    return f"⚠️  {text}"


def _bold(text: str) -> str:
    return f"\033[1m{text}\033[0m"


def _format_result(r: dict) -> str:
    """Format skill execution result for CLI output."""
    status = r.get("status", "ok")
    output = r.get("output", "")
    ci_delta = r.get("ci_delta", 0)

    status_icons = {
        "ok": "✅", "accepted": "✅", "delivered": "✅",
        "spec_approved": "✅", "discovery_complete": "✅",
        "error": "❌", "failed": "❌", "blocked": "⛔",
        "interview_started": "🔍", "spec_written": "📋",
        "test_prepared": "🧪", "discovery_auto_confirmed": "🔓",
        "acceptance_auto_confirmed": "🔓",
        "spec_auto_confirmed": "🔓",
        "awaiting_discovery": "📝",
    }
    icon = status_icons.get(status, "•")
    lines = [f"{icon} [{status}]"]
    if ci_delta:
        lines.append(f"   CI: {ci_delta:+.0f}")

    # Print full output (not truncate for CLI)
    if isinstance(output, str):
        lines.append(output)
    elif isinstance(output, dict):
        for k, v in output.items():
            lines.append(f"   {k}: {v}")

    return "\n".join(lines)


# ─── Commands ─────────────────────────────────────────────────────────────────

def cmd_run(args: argparse.Namespace) -> int:
    """Run full pipeline: explore → discover → spec → build → accept → ship."""
    task = args.task or args.task_var
    if not task:
        print(_err("Usage: neutron run <task>"))
        return 1

    print(_header(f"NEUTRON PIPELINE — {task}"))
    print(_info("Starting at /explore..."))

    r = skill_execution.run("workflow", task, {"step": "explore"})
    print(f"\n/explore: {r['status']}")

    # Discovery
    print(_info("Running /discovery interview..."))
    r = skill_execution.run("discovery", task, {"action": "start"})
    print(f"/discovery: {r['status']} — {r.get('questions_remaining', 0)} questions")
    print(f"\n{r['output']}")

    # SPEC
    print(_header("SPEC.md — USER REVIEW REQUIRED"))
    r = skill_execution.run("workflow", task, {"step": "spec"})
    print(_format_result(r))
    print("\n⏸  SPEC requires USER REVIEW before build can proceed.")
    print("   Run: neutron spec-approve")
    return 0


def cmd_discover(args: argparse.Namespace) -> int:
    """Run discovery interview for a project idea."""
    idea = args.idea
    if not idea:
        print(_err("Usage: neutron discover <project idea>"))
        return 1

    print(_header(f"DISCOVERY INTERVIEW — {idea}"))
    r = skill_execution.run("discovery", idea, {"action": "start"})
    print(_format_result(r))
    print(f"\n📝 Answer the questions above, then run:")
    print(f"   neutron discover-record ANSWERS...")
    print(f"   (or: neutron discover-record done_criteria='...' tech_stack='...')")
    return 0


def cmd_discover_record(args: argparse.Namespace) -> int:
    """Record answers to discovery interview."""
    idea = args.idea or "Project"
    # Parse answers from --answer flags or positional
    answers = {}
    for ans in (args.answers or []):
        if "=" in ans:
            k, v = ans.split("=", 1)
            answers[k.strip()] = v.strip()

    if not answers:
        print(_warn("No answers provided. Usage: neutron discover-record k1=v1 k2=v2 ..."))
        print("   neutron discover-record done_criteria='User can login' tech_stack='Python, Flask'")
        return 1

    r = skill_execution.run("discovery", idea, {"action": "record", "answers": answers})
    print(_format_result(r))
    return 0


def cmd_spec(args: argparse.Namespace) -> int:
    """Write SPEC.md and present for USER REVIEW."""
    task = args.task or "Project"
    spec_content = args.spec_content

    if spec_content:
        # User provided SPEC content — write and approve
        r = skill_execution.run("workflow", task, {
            "step": "spec",
            "write_spec": True,
            "spec_content": spec_content,
            "approved": True,
        })
    else:
        r = skill_execution.run("workflow", task, {"step": "spec"})

    print(_format_result(r))

    if r["status"] == "spec_written":
        print("\n📋 SPEC written. User review required before build.")
        print("   To approve: neutron spec-approve [notes]")
        print("   To edit: neutron spec-edit")
    return 0


def cmd_spec_approve(args: argparse.Namespace) -> int:
    """Approve SPEC — unlocks build."""
    task = args.task or "Project"
    r = skill_execution.run("workflow", task, {"step": "spec", "approved": True, "notes": args.notes or ""})
    print(_format_result(r))
    return 0


def cmd_build(args: argparse.Namespace) -> int:
    """Build implementation — requires SPEC approved."""
    task = args.task or "Build"
    r = skill_execution.run("workflow", task, {"step": "build"})
    print(_format_result(r))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    """Run verification."""
    task = args.task or "Verify"
    r = skill_execution.run("workflow", task, {"step": "verify"})
    print(_format_result(r))
    return 0


def cmd_accept(args: argparse.Namespace) -> int:
    """Run acceptance test."""
    task = args.task or "Acceptance"
    action = args.action

    if action == "prepare":
        r = skill_execution.run("acceptance_test", task, {"action": "prepare"})
    elif action == "pass":
        r = skill_execution.run("acceptance_test", task, {"action": "pass", "notes": args.notes or "User confirmed"})
    elif action == "fail":
        r = skill_execution.run("acceptance_test", task, {"action": "fail", "notes": args.notes or ""})
    else:
        r = skill_execution.run("acceptance_test", task, {"action": action or "prepare"})

    print(_format_result(r))
    return 0


def cmd_ship(args: argparse.Namespace) -> int:
    """Ship delivery — requires acceptance passed."""
    task = args.task or "Ship"
    r = skill_execution.run("workflow", task, {
        "step": "ship",
        "rating": args.rating,
        "notes": args.notes or "",
    })
    print(_format_result(r))

    if r["status"] == "delivered":
        s = rating_summarize()
        print(f"\n📦 Delivery recorded. Rating: {args.rating or '?'}/5")
        print(f"   Total shipments: {s['total']} | Avg rating: {s.get('average_rating', 'N/A')}")
    return 0


def cmd_auto(args: argparse.Namespace) -> int:
    """Control auto-confirm mode."""
    mode = args.mode

    if mode == "status":
        gates = auto_confirm.get_gates()
        print(_header("AUTO-CONFIRM STATUS"))
        print(f"Enabled: {'🔓 YES' if gates['enabled'] else '🔴 NO'}")
        print(f"Mode: {gates['mode']}")
        print(f"  Discovery:   {'SKIP' if gates['discovery'] else 'REQUIRED'}")
        print(f"  SPEC:        {'AUTO-APPROVE' if gates['spec'] else 'REQUIRED'}")
        print(f"  Acceptance:   {'AUTO-PASS' if gates['acceptance'] else 'REQUIRED'}")
        print(f"Notes: {gates['notes']}")

        # Show platform sync status
        print(_header("PLATFORM STATUS"))
        try:
            pstatus = get_platform_status()
            for plat, info in pstatus.get("platforms", {}).items():
                pp = info.get("permissionPromptsEnabled")
                aa = info.get("autoApprove")
                neu = info.get("env_NEUTRON_AUTO_CONFIRM", "")
                if pp is not None:
                    icon = "🔓" if not pp else "🔴"
                    print(f"  {icon} {plat}: permissionPromptsEnabled={pp}, autoApprove={aa}, NEUTRON_AUTO_CONFIRM={neu}")
                else:
                    count = info.get("count", 0)
                    icon = "⬜" if count == 0 else "🟡"
                    paths = info.get("paths", [])
                    print(f"  {icon} {plat}: {count} config file(s) found")
                    for p in paths:
                        print(f"       → {p}")
        except Exception as e:
            print(f"  ⚠️  Could not read platform status: {e}")

        return 0

    if mode == "platforms":
        print(_header("PLATFORM SYNC STATUS"))
        try:
            from engine.platform_sync import sync_all, disable_all
            if args.enable_platforms:
                result = sync_all(enabled=True)
            elif args.disable_platforms:
                result = disable_all()
            else:
                result = sync_all(enabled=auto_confirm.is_enabled())
            print(format_sync_results(result))
        except Exception as e:
            print(f"❌ Platform sync error: {e}")
        return 0

    # Set mode
    if mode == "toggle":
        r = auto_confirm.toggle()
    elif mode == "disable":
        r = auto_confirm.disable()
    else:
        r = auto_confirm.enable(mode=mode, notes=args.notes or "")

    print(_header("AUTO-CONFIRM"))
    if r.get("status") == "disabled":
        print("🔴 DISABLED — All gates require user action")
    else:
        print(f"🔓 ENABLED: {r.get('mode', mode)}")
        gates = r.get("gates", {})
        print(f"   Discovery:   {'SKIP' if gates.get('discovery') else 'REQUIRED'}")
        print(f"   SPEC:        {'AUTO-APPROVE' if gates.get('spec') else 'REQUIRED'}")
        print(f"   Acceptance:  {'AUTO-PASS' if gates.get('acceptance') else 'REQUIRED'}")
    print()
    print(r.get("message", ""))
    return 0


def cmd_checkpoint(args: argparse.Namespace) -> int:
    """Write or read checkpoint."""
    if args.read:
        r = skill_execution.run("checkpoint", args.task or "Read", {"action": "read"})
    elif args.handoff:
        r = skill_execution.run("checkpoint", args.task or "Handoff", {
            "action": "handoff",
            "notes": args.notes or "CLI handoff",
        })
    else:
        r = skill_execution.run("checkpoint", args.task or "Checkpoint", {
            "action": "write",
            "task": args.task or "Checkpoint",
            "notes": args.notes or "",
            "confidence": args.confidence or "medium",
        })
    print(_format_result(r))
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    """Show system status."""
    print(_header("NEUTRON EVO OS — System Status"))

    # Auto-confirm status
    gates = auto_confirm.get_gates()
    auto_status = "🔓 enabled" if gates["enabled"] else "🔴 disabled"
    print(f"Auto-confirm: {auto_status} ({gates['mode']})")

    # Health
    h = engine_audit()
    print(f"System CI: {h['overall_ci']:.1f} | Status: {h['status']}")
    print(f"Skills: {h['skill_count']} registered | Blocked: {len(h.get('blocked_skills', []))}")

    # Ratings
    s = rating_summarize()
    print(f"\n📦 Deliveries: {s['total']} | Avg rating: {s.get('average_rating') or 'N/A'}")

    # Decisions
    d = decisions_summarize()
    print(f"📝 User decisions: {d['total']}")

    # Routing
    if args.task:
        r = route_task(args.task)
        print(f"\n🔀 Route '{args.task}':")
        print(f"   → {r['skill']} (confidence={r['confidence']:.2f})")
        print(f"   {r.get('reasoning', '')}")

    return 0


def cmd_audit(args: argparse.Namespace) -> int:
    """Full CI audit."""
    print(_header("CI AUDIT"))
    h = engine_audit()
    print(f"Overall: {h['overall_ci']:.1f} | {h['status']}")

    entries = h.get("all_entries", {})
    if not entries:
        from engine.expert_skill_router import get_all_skill_entries
        entries = get_all_skill_entries()

    for skill in sorted(entries.keys()):
        e = entries[skill]
        ci = e.get("CI", 50)
        bar = "█" * (ci // 10) + "░" * (10 - ci // 10)
        status_icon = "🟢" if ci >= 70 else "🟡" if ci >= 40 else "🔴"
        print(f"  {skill:20} {bar} {ci:3} {status_icon}")

    if h.get("blocked_skills"):
        print(f"\n⛔ Blocked: {h['blocked_skills']}")
    return 0


def cmd_memory(args: argparse.Namespace) -> int:
    """Memory operations."""
    action = args.action or "status"
    # Sync: satellite projects (e.g. /mnt/data/projects/octa) lack skills/ directory.
    # Load _sync_to_hub directly from hub path via importlib.
    if action == "sync":
        import importlib
        import importlib.util
        hub = Path(os.environ.get("NEUTRON_HUB", str(_NEUTRON_ROOT)))
        spec = importlib.util.spec_from_file_location(
            "_sync_mod", hub / "skills" / "core" / "memory" / "logic" / "__init__.py"
        )
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        r = mod._sync_to_hub({"hub_root": args.hub or str(hub)})
        print(_format_result(r))
        return 0
    r = skill_execution.run("memory", args.task or "memory", {
        "action": action,
        "query": args.query,
        "file_path": args.file_path,
        "draft_id": args.draft_id,
        "hub_root": args.hub,
    })
    print(_format_result(r))
    return 0


def cmd_log(args: argparse.Namespace) -> int:
    """Show today's memory log."""
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = _NEUTRON_ROOT / "memory" / f"{today}.md"

    if not log_path.exists():
        print(_info(f"No memory log for today ({today})"))
        return 0

    content = log_path.read_text(errors="replace")
    # Show last 100 lines
    lines = content.splitlines()
    print(_header(f"MEMORY LOG — {today}"))
    print("\n".join(lines[-100:]))
    return 0


def cmd_decisions(args: argparse.Namespace) -> int:
    """Show recent user decisions."""
    from engine.user_decisions import get_recent
    decisions = get_recent(n=args.n or 10)
    print(_header("USER DECISIONS"))
    if not decisions:
        print(_info("No decisions recorded yet."))
        return 0
    for d in reversed(decisions):
        ts = d.get("timestamp", "")[:16]
        outcome = d.get("outcome", "?")
        print(f"[{ts}] {d.get('decision','')}")
        print(f"   context: {d.get('context','')[:80]}")
        print(f"   outcome: {outcome}")
    return 0


def cmd_route(args: argparse.Namespace) -> int:
    """Route a task to a skill."""
    if not args.task:
        print(_err("Usage: neutron route <task>"))
        return 1
    r = route_task(args.task)
    print(_header(f"ROUTE: {args.task}"))
    print(f"→ Skill: {r['skill']}")
    print(f"→ Confidence: {r['confidence']:.2f}")
    print(f"→ Reasoning: {r.get('reasoning','')}")
    if r.get("blocked"):
        print(f"⛔ BLOCKED: {r.get('block_reason','')}")
    return 0


def cmd_dream(args: argparse.Namespace) -> int:
    """Run Dream Cycle."""
    print(_header("DREAM CYCLE"))
    from engine.dream_engine import dream_cycle
    result = dream_cycle()
    if isinstance(result, str):
        result = json.loads(result)
    print(f"Status: {result.get('status','')}")
    print(f"Archived: {result.get('archived',0)} files")
    print(f"Distilled: {result.get('distilled',0)} files")
    print(f"Pruned: {result.get('pruned',0)} files")
    return 0


def cmd_version(args: argparse.Namespace) -> int:
    """Show version info."""
    from engine.expert_skill_router import audit as engine_audit
    from engine import auto_confirm
    from engine.rating import summarize as rating_summarize

    print(_header(f"NEUTRON EVO OS v{NEUTRON_VERSION}"))
    print(f"  Owner: Adam Wang (Vương Hoàng Tuấn)")
    print(f"  Philosophy: ∫f(t)dt — Functional Credibility Over Institutional Inertia")
    print(f"  NEUTRON_ROOT: {_NEUTRON_ROOT}")

    # Health
    health = engine_audit()
    print(f"\n  System Health: {health['status'].upper()}")
    print(f"  Overall CI: {health['overall_ci']}")
    print(f"  Skills: {health['skill_count']}")

    # Ratings
    ratings = rating_summarize()
    if ratings["total"] > 0:
        print(f"\n  Shipments: {ratings['total']} total, {ratings['rated']} rated")
        if ratings["average_rating"]:
            print(f"  Avg Rating: {ratings['average_rating']}/5")

    # Auto-confirm
    gates = auto_confirm.get_gates()
    mode = gates.get("mode", "disabled")
    icon = "🔓" if gates.get("enabled") else "🔴"
    print(f"\n  {icon} Auto-Confirm: {mode}")

    print()
    return 0


def cmd_gc(args: argparse.Namespace) -> int:
    """
    Garbage Collection: clean up disk space.
    Removes: archived/ over retention, __pycache__, *.pyc, old backups, test cache.
    """
    import glob

    print(_header("🗑️  Garbage Collection"))
    print(f"  NEUTRON_ROOT: {_NEUTRON_ROOT}\n")

    MEMORY_DIR = _NEUTRON_ROOT / "memory"
    ARCHIVED_DIR = MEMORY_DIR / "archived"
    COOKBOOKS_DIR = MEMORY_DIR / "cookbooks"
    BACKUP_DIR = _NEUTRON_ROOT / ".backup"

    deleted = []
    errors = []
    total_bytes = 0

    def _delete(path: Path, reason: str) -> None:
        nonlocal total_bytes
        if args.dry_run:
            size = path.stat().st_size if path.is_file() else 0
            print(f"  [DRY RUN] Delete: {path.relative_to(_NEUTRON_ROOT)} ({_format_size(size)}) — {reason}")
            return
        try:
            size = path.stat().st_size if path.is_file() else 0
            if path.is_file():
                path.unlink()
            elif path.is_dir():
                shutil.rmtree(path)
            total_bytes += size
            deleted.append(str(path.relative_to(_NEUTRON_ROOT)))
            print(f"  ✅ Deleted: {path.relative_to(_NEUTRON_ROOT)} ({_format_size(size)})")
        except Exception as e:
            print(f"  ❌ Failed: {path.relative_to(_NEUTRON_ROOT)} — {e}")
            errors.append(str(path))

    def _format_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB"]:
            if size < 1024:
                return f"{size:.1f}{unit}"
            size /= 1024
        return f"{size:.1f}GB"

    # 1. archived/ files beyond retention
    if ARCHIVED_DIR.exists():
        ret_days = args.retention if args.retention else 7
        cutoff = datetime.now() - timedelta(days=ret_days)
        count = len(list(ARCHIVED_DIR.iterdir()))
        print(f"  📦 archived/: {count} files | retention: {ret_days} days")
        for f in sorted(ARCHIVED_DIR.iterdir(), key=lambda x: x.stat().st_mtime):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    _delete(f, f"retention {ret_days} days")
            except Exception:
                pass

    # 2. .backup/ old files
    if BACKUP_DIR.exists():
        bak_days = args.backup_days if args.backup_days else 30
        cutoff = datetime.now() - timedelta(days=bak_days)
        count = len(list(BACKUP_DIR.iterdir()))
        print(f"  💾 .backup/: {count} files | retention: {bak_days} days")
        for f in sorted(BACKUP_DIR.iterdir(), key=lambda x: x.stat().st_mtime):
            try:
                mtime = datetime.fromtimestamp(f.stat().st_mtime)
                if mtime < cutoff:
                    _delete(f, f"backup retention {bak_days} days")
            except Exception:
                pass

    # 3. __pycache__ directories
    if args.pycache:
        print(f"  🐍 __pycache__ cleanup:")
        for root_dir in [_NEUTRON_ROOT, COOKBOOKS_DIR]:
            if not root_dir.exists():
                continue
            for pc in root_dir.rglob("__pycache__"):
                _delete(pc, "__pycache__")
            for pyc in root_dir.rglob("*.pyc"):
                _delete(pyc, "*.pyc")

    # 4. Test cache
    if args.tests:
        for pattern in ["tests/__pycache__", "tests/.pytest_cache", "*.pyc"]:
            for f in _NEUTRON_ROOT.glob(pattern):
                _delete(f, "test cache")

    # 5. Large unused files
    if args.large:
        print(f"  📁 Large files (>{args.large}MB) not in git:")
        for f in _NEUTRON_ROOT.rglob("*"):  # default: does NOT follow symlinks
            if not f.is_file():
                continue
            try:
                size_mb = f.stat().st_size / (1024 * 1024)
                if size_mb > args.large:
                    rel = f.relative_to(_NEUTRON_ROOT)
                    if not any(p in str(rel) for p in [".git", "node_modules", "archived"]):
                        _delete(f, f"large file ({size_mb:.0f}MB)")
            except Exception:
                pass

    # 6. data_*.json files in archived/ (external dumps from tests/agents)
    if args.data_json:
        json_files = list(ARCHIVED_DIR.glob("data_*.json"))
        count = len(json_files)
        print(f"  🗑️  data_*.json in archived/: {count} files")
        for f in json_files:
            _delete(f, "data_*.json dump")

    # 6b. Empty directories
    if args.empty:
        print("  📂 Empty directories:")
        for d in _NEUTRON_ROOT.rglob("*"):
            if d.is_dir() and not any(d.iterdir()):
                try:
                    d.rmdir()
                    print(f"  ✅ Removed empty dir: {d.relative_to(_NEUTRON_ROOT)}")
                except Exception:
                    pass

    print(f"\n{_bold('Summary')}")
    print(f"  Deleted: {len(deleted)} items")
    print(f"  Freed:   {_format_size(total_bytes)}")
    if errors:
        print(f"  Errors:  {len(errors)}")
    if args.dry_run:
        print(f"\n  ⚠️  DRY RUN — no files were actually deleted")
    print()
    return 0


def cmd_protect(args: argparse.Namespace) -> int:
    """
    Run Upgrade Protection Protocol: backup protected files before upgrade.
    Per RULES.md — MANDATORY before git pull, pip install, npm install, install scripts.
    """
    import shutil
    import glob

    print(_header("🔒 Upgrade Protection Protocol"))
    print(f"  NEUTRON_ROOT: {_NEUTRON_ROOT}\n")

    # Protected files list
    protected = [
        ".env",
        ".env.local",
        "memory/shipments.json",
        "memory/user_decisions.json",
        "memory/.mcp_config.json",
        "memory/.auto_confirm.json",
        "memory/handoff*.md",
        "memory/rss*.json",
        "USER.md",
    ]

    backed_up = []
    skipped = []
    errors = []

    for pattern in protected:
        full_pattern = _NEUTRON_ROOT / pattern.replace("*", "")
        if "*" in pattern:
            # Glob for patterns like handoff*.md
            matches = list(_NEUTRON_ROOT.glob(pattern))
        else:
            matches = [full_pattern] if full_pattern.exists() else []

        for path in matches:
            if not path.is_file():
                continue
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_name = f"{path.name}.{ts}.bak"
            backup_path = _NEUTRON_ROOT / ".backup" / backup_name
            if args.dry_run:
                print(f"  [DRY RUN] Would backup: {path.relative_to(_NEUTRON_ROOT)} → .backup/{backup_name}")
                backed_up.append(str(path))
                continue
            try:
                (_NEUTRON_ROOT / ".backup").mkdir(exist_ok=True)
                shutil.copy2(path, backup_path)
                print(f"  ✅ Backed up: {path.relative_to(_NEUTRON_ROOT)}")
                backed_up.append(str(path))
            except Exception as e:
                print(f"  ❌ Failed: {path.relative_to(_NEUTRON_ROOT)} — {e}")
                errors.append(str(path))

    print(f"\n{_bold('Summary')}")
    print(f"  Backed up: {len(backed_up)} files")
    if errors:
        print(f"  Errors: {len(errors)}")
    if args.dry_run:
        print(f"\n  ⚠️  DRY RUN — no files were actually backed up")
    else:
        print(f"  📁 Backup location: {_NEUTRON_ROOT}/.backup/")
        print(f"\n  Next: safe to run git pull / pip install / install.sh")
    print()
    return 0


# ─── Argument Parser ──────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="neutron",
        description=f"NEUTRON EVO OS v{NEUTRON_VERSION} — AI Agent Operating System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=f"""
Version: {NEUTRON_VERSION}
Examples:
  neutron version                Show version info
  neutron protect                Run Upgrade Protection Protocol (backup before upgrade)
  neutron discover "Build a trading bot"
  neutron spec "Build auth system" --content "..."
  neutron auto full
  neutron auto spec_only
  neutron accept prepare
  neutron accept pass --notes "Works great!"
  neutron ship --rating 4 --notes "Fast delivery"
  neutron status
  neutron audit
  neutron log
  neutron decisions
        """,
    )

    sub = parser.add_subparsers(dest="command")

    # run
    p = sub.add_parser("run", help="Run full pipeline")
    p.add_argument("task", nargs="?", help="Task description")
    p.set_defaults(func=cmd_run)

    # discover
    p = sub.add_parser("discover", help="Run discovery interview")
    p.add_argument("idea", nargs="?", help="Project idea/prompt")
    p.set_defaults(func=cmd_discover)

    # discover-record
    p = sub.add_parser("discover-record", help="Record discovery answers")
    p.add_argument("idea", nargs="?", default="Project", help="Project name")
    p.add_argument("answers", nargs="*", help="key=value pairs, e.g. done_criteria='User logs in'")
    p.set_defaults(func=cmd_discover_record)

    # spec
    p = sub.add_parser("spec", help="Write SPEC.md (USER REVIEW gate)")
    p.add_argument("task", nargs="?", help="Task name")
    p.add_argument("--content", dest="spec_content", help="Full SPEC.md content to write")
    p.set_defaults(func=cmd_spec)

    # spec-approve
    p = sub.add_parser("spec-approve", help="Approve SPEC — unlocks build")
    p.add_argument("task", nargs="?", help="Task name")
    p.add_argument("notes", nargs="?", help="Approval notes")
    p.set_defaults(func=cmd_spec_approve)

    # build
    p = sub.add_parser("build", help="Build implementation (requires SPEC approved)")
    p.add_argument("task", nargs="?", help="Task description")
    p.set_defaults(func=cmd_build)

    # verify
    p = sub.add_parser("verify", help="Run verification")
    p.add_argument("task", nargs="?", help="Task name")
    p.set_defaults(func=cmd_verify)

    # accept
    p = sub.add_parser("accept", help="Acceptance test")
    p.add_argument("task", nargs="?", help="Task name")
    p.add_argument("action", nargs="?", default="prepare", choices=["prepare", "pass", "fail"])
    p.add_argument("--notes", dest="notes", help="Notes for pass/fail")
    p.set_defaults(func=cmd_accept)

    # ship
    p = sub.add_parser("ship", help="Ship delivery (requires acceptance)")
    p.add_argument("task", nargs="?", help="Task name")
    p.add_argument("--rating", type=int, choices=[1, 2, 3, 4, 5], help="User rating 1-5")
    p.add_argument("--notes", dest="notes", help="Delivery notes")
    p.set_defaults(func=cmd_ship)

    # auto
    p = sub.add_parser("auto", help="Auto-confirm control")
    p.add_argument("mode", nargs="?", default="status",
                   choices=["full", "spec_only", "acceptance_only", "spec_and_acceptance",
                            "discovery_only", "disable", "toggle", "status", "platforms"])
    p.add_argument("--notes", dest="notes", help="Notes for audit trail")
    p.add_argument("--platforms", dest="enable_platforms", action="store_true",
                   help="Force sync platforms (enable mode)")
    p.add_argument("--platforms-restore", dest="disable_platforms", action="store_true",
                   help="Force restore platforms (disable mode)")
    p.set_defaults(func=cmd_auto)

    # checkpoint
    p = sub.add_parser("checkpoint", help="Write or read checkpoint")
    p.add_argument("task", nargs="?", help="Task description")
    p.add_argument("--read", action="store_true", help="Read latest checkpoint")
    p.add_argument("--handoff", action="store_true", help="Handoff mode")
    p.add_argument("--notes", dest="notes", help="Notes")
    p.add_argument("--confidence", dest="confidence", choices=["low", "medium", "high"])
    p.set_defaults(func=cmd_checkpoint)

    # status
    p = sub.add_parser("status", help="System status")
    p.add_argument("task", nargs="?", help="Optional: route this task")
    p.set_defaults(func=cmd_status)

    # audit
    p = sub.add_parser("audit", help="Full CI audit")
    p.set_defaults(func=cmd_audit)

    # memory
    p = sub.add_parser("memory", help="Memory operations")
    p.add_argument("action", nargs="?", choices=["log", "archive", "search", "dream", "status", "sync", "pending", "approve", "reject"], default="status")
    p.add_argument("--hub", dest="hub", help="Hub root path (for sync action)")
    p.add_argument("--draft-id", dest="draft_id", help="Draft ID (for approve/reject actions)")
    p.add_argument("task", nargs="?", help="Task for log action")
    p.add_argument("--query", dest="query", help="Search query")
    p.add_argument("--file", dest="file_path", help="File to archive")
    p.set_defaults(func=cmd_memory)

    # log
    p = sub.add_parser("log", help="Show today's memory log")
    p.set_defaults(func=cmd_log)

    # decisions
    p = sub.add_parser("decisions", help="Show recent user decisions")
    p.add_argument("-n", type=int, default=10, help="Number of decisions to show")
    p.set_defaults(func=cmd_decisions)

    # route
    p = sub.add_parser("route", help="Route a task to skill")
    p.add_argument("task", help="Task description")
    p.set_defaults(func=cmd_route)

    # dream
    p = sub.add_parser("dream", help="Run Dream Cycle")
    p.set_defaults(func=cmd_dream)

    # version
    p = sub.add_parser("version", help="Show version info")
    p.set_defaults(func=cmd_version)

    # gc
    p = sub.add_parser("gc", help="Garbage collection — clean up disk space")
    p.add_argument("--dry-run", action="store_true", help="Show what would be deleted without deleting")
    p.add_argument("--retention", type=int, default=7, help="archived/ retention in days (default: 7)")
    p.add_argument("--backup-days", type=int, default=30, help=".backup/ retention in days (default: 30)")
    p.add_argument("--pycache", action="store_true", help="Delete __pycache__ and *.pyc files")
    p.add_argument("--tests", action="store_true", help="Delete test cache (__pycache__, .pytest_cache)")
    p.add_argument("--large", type=float, metavar="MB", help="Delete files larger than N MB not in git")
    p.add_argument("--empty", action="store_true", help="Remove empty directories")
    p.add_argument("--data-json", action="store_true", help="Delete data_*.json files in archived/ (test/agent dumps)")
    p.set_defaults(func=cmd_gc)

    # protect
    p = sub.add_parser("protect", help="Run Upgrade Protection Protocol — backup protected files before upgrade")
    p.add_argument("--dry-run", action="store_true", help="Show what would be backed up without backing up")
    p.set_defaults(func=cmd_protect)

    return parser


# ─── Main ────────────────────────────────────────────────────────────────────

def main():
    parser = build_parser()
    args = parser.parse_args()  # argparse auto-handles -h/--help at subparser level

    # Default: show status
    if args.command is None:
        args.command = "status"
        args.task = None
        args.func = cmd_status

    try:
        code = args.func(args)
        sys.exit(code or 0)
    except KeyboardInterrupt:
        print("\nAborted.")
        sys.exit(130)
    except Exception as e:
        print(_err(f"Error: {e}"))
        if os.environ.get("NEUTRON_DEBUG"):
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
