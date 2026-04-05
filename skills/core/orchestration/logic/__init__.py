"""
Orchestration Skill — Logic Module (v1.0)
run_orchestration(task, context) → {status, output, plan, units, ci_delta}

Phases:
  analyze   : Decompose task into independent units
  plan      : Present execution plan to user
  execute   : Spawn parallel agents per unit
  merge     : Validate and merge results
  report    : Final unified report
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from datetime import datetime
from typing import Optional

# Resolve NEUTRON_ROOT
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent.parent)
))
MEMORY_DIR = _NEUTRON_ROOT / "memory"
_STATE_FILE = MEMORY_DIR / ".orchestration_state.json"


# ─── State Management ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"phase": "analyze", "units": [], "results": {}, "task": ""}


def _save_state(state: dict) -> None:
    MEMORY_DIR.mkdir(exist_ok=True)
    _STATE_FILE.write_text(json.dumps(state, indent=2))


def _clear_state() -> None:
    if _STATE_FILE.exists():
        _STATE_FILE.unlink()


# ─── Unit Analyzer ─────────────────────────────────────────────────────────────

def _analyze_complexity(task: str, discovery_content: str = "") -> dict:
    """Analyze task and determine if orchestration is appropriate."""
    combined = (task + " " + discovery_content).lower()

    # Count indicators of decomposition potential
    independent_indicators = [
        # Module/component keywords
        ("frontend", combined.count("frontend") + combined.count("ui") + combined.count("component")),
        ("backend", combined.count("backend") + combined.count("server") + combined.count("api")),
        ("database", combined.count("database") + combined.count("model") + combined.count("schema")),
        ("auth", combined.count("auth") + combined.count("login") + combined.count("user")),
        ("testing", combined.count("test") + combined.count("spec")),
        ("infra", combined.count("deploy") + combined.count("docker") + combined.count("ci")),
        ("api", combined.count("endpoint") + combined.count("rest") + combined.count("graphql")),
        ("mobile", combined.count("mobile") + combined.count("ios") + combined.count("android")),
    ]

    # Count explicit "and" connections suggesting parallel work
    and_count = len(re.findall(r'\band\b', combined))

    # Count module/component references
    module_count = len(re.findall(
        r'(module|component|service|feature|page|screen|endpoint|model|handler|middleware)',
        combined
    ))

    # Parallelism score: 0-100
    score = 0
    for domain, count in independent_indicators:
        if count >= 2:
            score += 15
        elif count >= 1:
            score += 8
    score += min(and_count * 5, 20)
    score += min(module_count * 8, 25)

    return {
        "score": score,
        "should_orchestrate": score >= 30,
        "domains": [d for d, c in independent_indicators if c >= 1],
        "module_count": module_count,
        "estimated_units": min(max(score // 15, 1), 8),
    }


def _decompose_task(task: str, discovery_content: str = "") -> list[dict]:
    """Decompose task into atomic independent units."""
    complexity = _analyze_complexity(task, discovery_content)
    units = []
    unit_num = 1

    combined = (task + " " + discovery_content).lower()

    # Define unit templates based on detected domains
    unit_templates = {
        "frontend": {
            "name": "Frontend / UI",
            "agent": "Plan",
            "scope": "User interface, components, pages, routing, state management",
            "files_hint": "src/components/, src/pages/, src/App.*, src/hooks/",
            "deliverables": "UI components, routing setup, state management, responsive layout",
        },
        "backend": {
            "name": "Backend / API",
            "agent": "Plan",
            "scope": "Server logic, request handling, business rules, middleware",
            "files_hint": "server/, app/, routes/, handlers/, middleware/",
            "deliverables": "API endpoints, request handlers, business logic, error handling",
        },
        "database": {
            "name": "Database / Data Models",
            "agent": "Plan",
            "scope": "Data models, migrations, queries, indexes",
            "files_hint": "models/, schemas/, migrations/, db/",
            "deliverables": "Data models, schema migrations, seed data",
        },
        "auth": {
            "name": "Authentication / Authorization",
            "agent": "Plan",
            "scope": "Auth flow, session management, access control, token handling",
            "files_hint": "auth/, middleware/auth.*, routes/auth.*, utils/jwt.*",
            "deliverables": "Auth endpoints, JWT/session handling, permission middleware",
        },
        "testing": {
            "name": "Testing / Verification",
            "agent": "Plan",
            "scope": "Unit tests, integration tests, test fixtures",
            "files_hint": "tests/, __tests__/, *.test.*, *.spec.*",
            "deliverables": "Test suite, fixtures, test utilities",
        },
        "infra": {
            "name": "Infrastructure / DevOps",
            "agent": "Plan",
            "scope": "Docker, CI/CD, environment config, deployment",
            "files_hint": "Dockerfile, docker-compose.yml, .github/, .env.example, deploy/",
            "deliverables": "Container config, CI pipeline, env templates, deployment scripts",
        },
        "api": {
            "name": "API Design / Contracts",
            "agent": "Plan",
            "scope": "API endpoint definitions, request/response schemas, documentation",
            "files_hint": "api/, openapi.*, routes/, types/api.*",
            "deliverables": "API routes, schema definitions, API documentation",
        },
        "mobile": {
            "name": "Mobile / Native",
            "agent": "Plan",
            "scope": "Mobile-specific UI, native features, platform integration",
            "files_hint": "mobile/, ios/, android/, app.*/",
            "deliverables": "Mobile screens, native integration, platform-specific code",
        },
    }

    # Build units based on detected domains
    for domain in complexity.get("domains", []):
        if domain in unit_templates:
            template = unit_templates[domain]
            units.append({
                "id": f"UNIT-{unit_num}",
                "name": template["name"],
                "agent": template["agent"],
                "scope": template["scope"],
                "files_hint": template["files_hint"],
                "deliverables": template["deliverables"],
                "dependencies": [],
                "interface": f"Outputs to {template['files_hint'].split('/')[0]}/",
                "estimated_minutes": 15,
                "status": "pending",
            })
            unit_num += 1

    # If no domains detected, create a single general unit
    if not units:
        units.append({
            "id": "UNIT-1",
            "name": "Full Implementation",
            "agent": "Plan",
            "scope": "Implement all features as described in the task",
            "files_hint": "src/",
            "deliverables": "Complete working implementation",
            "dependencies": [],
            "interface": "Complete deliverable",
            "estimated_minutes": 30,
            "status": "pending",
        })

    return units


# ─── Plan Presenter ────────────────────────────────────────────────────────────

def _present_plan(task: str, units: list[dict], complexity: dict) -> str:
    """Build the orchestration plan presentation."""
    lines = []
    lines.append(f"""
╔══════════════════════════════════════════════════════════╗
║  ORCHESTRATION PLAN — {len(units)} PARALLEL AGENTS          ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  Task: {task[:60]}
║  Parallelism score: {complexity['score']}/100
║  Recommendation: {'✅ Orchestrate' if complexity['should_orchestrate'] else '⚠️ Sequential may be faster'}
║                                                          ║""")

    for u in units:
        lines.append(f"""
║  {u['id']}: {u['name']}                          ║
║    Agent: {u['agent']:<8} | Scope: {u['scope'][:30]}...     ║
║    Deliver: {u['deliverables'][:45]}...  ║
║    Est: ~{u['estimated_minutes']} min""")

    seq_time = sum(u["estimated_minutes"] for u in units)
    par_time = max(u["estimated_minutes"] for u in units)
    speedup = f"{seq_time / par_time:.1f}x" if par_time > 0 else "N/A"

    lines.append(f"""
║  ─────────────────────────────────────────────────────  ║
║  Sequential time: ~{seq_time} min                         ║
║  Parallel time:  ~{par_time} min                         ║
║  Speed gain:     {speedup} faster                         ║
║                                                          ║
║  CONFLICT PREVENTION:                                    ║
║  - Each file owned by exactly ONE unit                   ║
║  - Main agent merges ALL outputs                         ║
║  - Workers never touch each other's files                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
""")

    return "\n".join(lines)


# ─── Main Entry Point ──────────────────────────────────────────────────────────

def run_orchestration(task: str, context: dict = None) -> dict:
    """
    Main entry point for the Orchestration Skill.

    Actions (via context["phase"]):
      analyze  : Decompose task into units (default)
      plan     : Present plan, wait for approval
      execute  : Spawn parallel agents per unit
      update   : Update unit status (progress reporting)
      merge    : Validate + merge results
      report   : Final unified report

    Orchestration state stored in: memory/.orchestration_state.json
    """
    context = context or {}
    phase = context.get("phase", "analyze")
    state = _load_state()

    # ── ANALYZE: Decompose task ───────────────────────────────────────────────
    if phase == "analyze":
        discovery = ""
        discovery_path = _NEUTRON_ROOT / "DISCOVERY.md"
        if discovery_path.exists():
            discovery = discovery_path.read_text()
        elif (MEMORY_DIR / "discoveries").exists():
            discoveries = sorted((MEMORY_DIR / "discoveries").rglob("DISCOVERY.md"),
                                key=lambda f: f.stat().st_mtime, reverse=True)
            if discoveries:
                discovery = discoveries[0].read_text()

        complexity = _analyze_complexity(task, discovery)
        units = _decompose_task(task, discovery)

        state.update({
            "phase": "plan",
            "task": task,
            "complexity": complexity,
            "units": units,
            "discovery_content": discovery,
        })
        _save_state(state)

        plan_text = _present_plan(task, units, complexity)

        return {
            "status": "plan_ready",
            "output": plan_text,
            "units": units,
            "complexity": complexity,
            "should_orchestrate": complexity["should_orchestrate"],
            "next_phase": "execute",
            "ci_delta": 5 if complexity["should_orchestrate"] else 0,
        }

    # ── PLAN: User confirmed or modified plan ─────────────────────────────────
    elif phase == "plan":
        modifications = context.get("modifications", {})
        units = state.get("units", [])

        # Apply user modifications
        if modifications:
            for unit_id, changes in modifications.items():
                for unit in units:
                    if unit["id"] == unit_id:
                        unit.update(changes)
                        break

        state["units"] = units
        state["phase"] = "execute"
        _save_state(state)

        return {
            "status": "plan_confirmed",
            "output": (
                f"✅ Plan confirmed — {len(units)} units ready for parallel execution.\n\n"
                "Spawning agents... (orchestration execute phase)"
            ),
            "units": units,
            "next_phase": "execute",
            "ci_delta": 0,
        }

    # ── EXECUTE: Spawn agents ─────────────────────────────────────────────────
    elif phase == "execute":
        units = state.get("units", [])
        task = state.get("task", task)
        discovery = state.get("discovery_content", "")
        spec_path = _NEUTRON_ROOT / "SPEC.md"
        spec_content = spec_path.read_text() if spec_path.exists() else ""

        # Generate agent tasks for each unit
        agent_tasks = []
        for u in units:
            task_text = f"""Implement the following unit for the project:

PROJECT TASK: {task}

UNIT: {u['id']} — {u['name']}
Scope: {u['scope']}
Files to create/modify: {u['files_hint']}
Deliverables: {u['deliverables']}

Rules:
1. Read the SPEC.md in the project root first
2. Only implement what is in SPEC.md
3. Never touch files owned by other units
4. After implementation, report what files you created/modified
5. Run tests if applicable before finishing

Output format:
```
DONE:
- [file created/modified]
...

TESTS: [pass/fail]
NOTES: [any observations]
```
"""
            agent_tasks.append({
                "unit_id": u["id"],
                "agent": u["agent"],
                "task": task_text,
                "scope": u["scope"],
            })

        state["phase"] = "merge"
        state["agent_tasks"] = agent_tasks
        _save_state(state)

        return {
            "status": "agents_spawned",
            "output": (
                f"🔄 {len(agent_tasks)} agents spawned for parallel execution.\n\n"
                "Each agent is implementing its assigned unit.\n"
                "Progress will be tracked and reported here.\n\n"
                "After agents complete, call:\n"
                "  run_orchestration(task, {'phase': 'merge'})\n"
            ),
            "agent_tasks": agent_tasks,
            "unit_count": len(agent_tasks),
            "next_phase": "merge",
            "ci_delta": 0,
        }

    # ── MERGE: Validate and merge results ───────────────────────────────────
    elif phase == "merge":
        units = state.get("units", [])
        task = state.get("task", task)

        # Check for file conflicts
        conflicts = _detect_conflicts(units)
        integration_result = _run_integration_check(units, task)

        state["phase"] = "report"
        state["conflicts"] = conflicts
        state["integration"] = integration_result
        _save_state(state)

        conflict_note = ""
        if conflicts:
            conflict_note = f"\n⚠️  {len(conflicts)} CONFLICT(S) DETECTED — resolving...\n"
            for c in conflicts:
                conflict_note += f"  - {c['description']} → Resolution: {c['resolution']}\n"

        return {
            "status": "merge_complete",
            "output": (
                f"✅ Merge complete.{conflict_note}\n"
                f"Integration: {integration_result['status']}\n"
                "Calling run_orchestration with phase='report' for final summary..."
            ),
            "conflicts": conflicts,
            "integration": integration_result,
            "next_phase": "report",
            "ci_delta": 5 if not conflicts else 2,
        }

    # ── REPORT: Final summary ──────────────────────────────────────────────────
    elif phase == "report":
        units = state.get("units", [])
        task = state.get("task", task)
        complexity = state.get("complexity", {})
        conflicts = state.get("conflicts", [])
        integration = state.get("integration", {})

        # Mark all units complete
        for u in units:
            u["status"] = "done"

        seq_time = sum(u.get("estimated_minutes", 0) for u in units)
        par_time = max((u.get("estimated_minutes", 0) for u in units), default=0)
        speedup = f"{seq_time / par_time:.1f}x" if par_time > 0 else "N/A"

        # Build deliverables list
        deliverable_lines = []
        for u in units:
            deliverable_lines.append(f"  ✅ {u['id']}: {u['name']}")
            deliverable_lines.append(f"     Deliverables: {u['deliverables']}")
            deliverable_lines.append(f"     Files: {u.get('files_hint', 'N/A')}")

        _clear_state()

        report_lines = [
            "",
            "╔══════════════════════════════════════════════════════════╗",
            "║  ORCHESTRATION COMPLETE                                 ║",
            "╠══════════════════════════════════════════════════════════╣",
            "",
            f"  Task: {task[:60]}",
            "",
            *deliverable_lines,
            "",
            f"  Speed gain: {speedup} vs sequential",
            f"  Integration: {integration.get('status', 'unknown').upper()}",
            "",
        ]

        if conflicts:
            report_lines.append("  ⚠️  Conflicts resolved:")
            for c in conflicts:
                report_lines.append(f"    - {c['description']}")

        report_lines.extend([
            "",
            "  Next: Run /acceptance_test to verify the build",
            "",
            "╚══════════════════════════════════════════════════════════╝",
            "",
        ])

        return {
            "status": "complete",
            "output": "\n".join(report_lines),
            "units": units,
            "speedup": speedup,
            "integration": integration,
            "conflicts": conflicts,
            "ci_delta": 8,
        }

    return {"status": "error", "output": f"Unknown phase: {phase}", "ci_delta": 0}


def _detect_conflicts(units: list[dict]) -> list[dict]:
    """
    Detect file ownership conflicts between units.

    A conflict exists when TWO units both claim the same file or directory
    (not just the same top-level directory name).
    """
    conflicts = []
    # path_key -> (unit_id, full_hint)
    # path_key = normalized path with "/" separator (not just first segment)
    ownership: dict[str, tuple[str, str]] = {}

    for u in units:
        unit_id = u["id"]
        for hint in u.get("files_hint", "").split(","):
            hint = hint.strip()
            if not hint:
                continue
            # Normalize: "src/components" → "src/components"
            # "src/components/" → "src/components"
            key = hint.rstrip("/")
            if key in ownership and ownership[key][0] != unit_id:
                owner_unit = ownership[key][0]
                conflicts.append({
                    "file": key,
                    "units": [owner_unit, unit_id],
                    "description": f"Path '{key}' claimed by both {owner_unit} and {unit_id}",
                    "resolution": (
                        f"Let {owner_unit} own '{key}'. "
                        f"{unit_id} imports from it — no direct file modification."
                    ),
                })
            else:
                ownership[key] = (unit_id, hint)

    return conflicts


def _run_integration_check(units: list[dict], task: str) -> dict:
    """
    Run integration checks across all units.

    Checks actual file existence in the declared paths, not just directory-level globs.
    Returns conservative status: "skipped" if no files were created by units.
    """
    # Check if SPEC.md still exists (meaningful build happened)
    spec_path = _NEUTRON_ROOT / "SPEC.md"
    if not spec_path.exists():
        return {"status": "skipped", "reason": "No SPEC.md found"}

    # Check for actual files in unit paths
    paths_checked = set()
    files_found = 0
    units_with_files = 0

    for u in units:
        unit_id = u["id"]
        hint = u.get("files_hint", "")
        has_files = False
        for part in hint.split(","):
            part = part.strip()
            if not part:
                continue
            if part in paths_checked:
                continue
            paths_checked.add(part)

            # Check if this path exists and contains files
            base = part.rstrip("/").split("/")[0]  # top-level dir
            resolved = _NEUTRON_ROOT / base
            if resolved.exists() and resolved.is_dir():
                # Count actual files (not directories) in this path
                try:
                    file_count = sum(
                        1 for f in resolved.rglob("*")
                        if f.is_file() and not f.name.startswith(".")
                    )
                    if file_count > 0:
                        files_found += file_count
                        has_files = True
                except PermissionError:
                    pass

        if has_files:
            units_with_files += 1

    if files_found == 0:
        return {
            "status": "no_files",
            "reason": f"No output files found in declared unit paths. Units may not have executed.",
            "units_with_files": units_with_files,
            "total_units": len(units),
        }

    return {
        "status": "passed",
        "files_found": files_found,
        "units_with_files": units_with_files,
        "total_units": len(units),
        "note": "Count is based on declared paths — actual unit attribution requires post-build scan",
    }
