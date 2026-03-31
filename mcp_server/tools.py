"""
NEUTRON EVO OS — MCP Tools
NEUTRON skills exposed as MCP tools via skill_execution.run().
"""
from __future__ import annotations

import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def list_tools():
    """Return the list of MCP tools (one per NEUTRON skill)."""
    return [
        {
            "name": "neutron_checkpoint",
            "description": "Write, read, or handoff a session checkpoint",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["write", "read", "handoff"],
                        "description": "Checkpoint action",
                    },
                    "task": {"type": "string", "description": "Task description"},
                    "notes": {"type": "string", "description": "Additional notes"},
                    "confidence": {
                        "type": "string",
                        "enum": ["low", "medium", "high"],
                        "description": "Confidence level",
                    },
                },
                "required": ["action", "task"],
            },
        },
        {
            "name": "neutron_context",
            "description": "Audit NEUTRON context files (P0/P1/P2 priority order)",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Audit task description"},
                },
                "required": ["task"],
            },
        },
        {
            "name": "neutron_discovery",
            "description": "Run discovery interview before building — ask user 12 clarifying questions",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["start", "record", "status"],
                        "description": "start=begin interview, record=save answers, status=check progress",
                    },
                    "task": {
                        "type": "string",
                        "description": "User's project idea/prompt/spec to analyze",
                    },
                    "answers": {
                        "type": "object",
                        "description": "User's answers to interview questions (for record action)",
                    },
                },
                "required": ["action"],
            },
        },
        {
            "name": "neutron_spec",
            "description": "Write SPEC.md from discovery output — presents for USER REVIEW before build",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "task": {"type": "string", "description": "Task/project name"},
                    "write_spec": {
                        "type": "boolean",
                        "description": "If true, write SPEC.md to disk",
                    },
                    "spec_content": {
                        "type": "string",
                        "description": "Full SPEC.md content to write",
                    },
                    "approved": {
                        "type": "boolean",
                        "description": "User approval of SPEC (hard gate — must be true before build)",
                    },
                    "notes": {
                        "type": "string",
                        "description": "User's notes/change requests",
                    },
                },
                "required": ["task"],
            },
        },
        {
            "name": "neutron_memory",
            "description": "Memory operations: log, archive, search, dream, status",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["log", "archive", "search", "dream", "status"],
                        "description": "Memory action",
                    },
                    "task": {"type": "string", "description": "Task description"},
                    "query": {"type": "string", "description": "Search query (for search action)"},
                    "file_path": {
                        "type": "string",
                        "description": "File path (for archive action)",
                    },
                    "notes": {"type": "string", "description": "Additional notes"},
                },
                "required": ["action", "task"],
            },
        },
        {
            "name": "neutron_workflow",
            "description": "Execute a workflow step: explore, discovery, spec, build, acceptance, ship",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "step": {
                        "type": "string",
                        "enum": ["explore", "discovery", "spec", "build", "verify", "acceptance", "ship"],
                        "description": "Workflow step (discovery, spec, acceptance are HUMAN GATES)",
                    },
                    "task": {"type": "string", "description": "Task description"},
                    "criteria": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Acceptance criteria (for spec step)",
                    },
                    "notes": {"type": "string", "description": "Additional notes"},
                    "action": {
                        "type": "string",
                        "description": "Sub-action for specific steps (e.g., 'prepare' for acceptance)",
                    },
                    "rating": {
                        "type": "integer",
                        "description": "User rating 1-5 (for ship step)",
                    },
                },
                "required": ["step", "task"],
            },
        },
        {
            "name": "neutron_acceptance",
            "description": "Run acceptance test — USER must confirm the build works before ship",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["prepare", "pass", "fail", "status"],
                        "description": "prepare=generate test, pass=user confirms, fail=user rejects",
                    },
                    "task": {"type": "string", "description": "Task description"},
                    "notes": {
                        "type": "string",
                        "description": "Notes (for pass/fail actions)",
                    },
                },
                "required": ["action", "task"],
            },
        },
        {
            "name": "neutron_engine",
            "description": "Engine operations: CI audit, task routing, observer control",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "enum": ["audit", "route", "observer_start", "observer_stop"],
                        "description": "Engine action",
                    },
                    "task": {"type": "string", "description": "Task (for route action)"},
                    "root": {
                        "type": "string",
                        "description": "Directory to watch (for observer_start)",
                    },
                    "debounce_seconds": {
                        "type": "integer",
                        "description": "Debounce seconds (for observer_start)",
                    },
                },
                "required": ["action", "task"],
            },
        },
        {
            "name": "neutron_audit",
            "description": "Full system health check — returns CI status, user ratings, recent decisions",
            "inputSchema": {"type": "object", "properties": {}},
        },
        {
            "name": "neutron_auto_confirm",
            "description": "Enable or disable auto-confirm mode — skip USER REVIEW gates",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "mode": {
                        "type": "string",
                        "enum": ["full", "spec_only", "acceptance_only", "spec_and_acceptance",
                                 "discovery_only", "disable", "toggle"],
                        "description": "Auto-confirm mode (default=toggle)",
                    },
                    "notes": {"type": "string", "description": "Notes for audit trail"},
                },
                "required": [],
            },
        },
    ]


def call_tool(name: str, arguments: dict) -> dict:
    """Execute the named MCP tool, routing to skill_execution.run()."""
    from engine import skill_execution

    # Extract task without mutating caller's dict
    task = arguments.get("task", "")
    tool_to_skill = {
        "neutron_checkpoint": "checkpoint",
        "neutron_context": "context",
        "neutron_memory": "memory",
        "neutron_workflow": "workflow",
        "neutron_engine": "engine",
        "neutron_audit": "engine",  # audit is a special engine action
        "neutron_discovery": "discovery",
        "neutron_spec": "workflow",  # spec is a workflow step
        "neutron_acceptance": "acceptance_test",
        "neutron_auto_confirm": "workflow",  # auto is a workflow step
    }
    skill_name = tool_to_skill.get(name)

    if not skill_name:
        return {
            "content": [{"type": "text", "text": f"Unknown tool: {name}"}],
        }

    # Handle special cases
    if name == "neutron_audit":
        args = {"action": "audit", "task": "system audit"}
        return _run_skill("engine", "system audit", args)

    if name == "neutron_discovery":
        return _run_skill("discovery", task, arguments)

    if name == "neutron_spec":
        return _run_skill("workflow", task, {"step": "spec", **arguments})

    if name == "neutron_acceptance":
        return _run_skill("acceptance_test", task, arguments)

    if name == "neutron_auto_confirm":
        return _run_skill("workflow", task, {"step": "auto", **arguments})

    return _run_skill(skill_name, task, arguments)


def _run_skill(skill_name: str, task: str, arguments: dict) -> dict:
    """Run a skill and format the result for MCP response."""
    from engine import skill_execution

    try:
        result = skill_execution.run(skill_name, task, arguments)
    except Exception as e:
        result = {"status": "error", "output": str(e), "ci_delta": 0}

    status = result.get("status", "ok")
    output = result.get("output", "")

    if isinstance(output, dict):
        output_text = str(output)
    elif isinstance(output, str):
        output_text = output
    else:
        output_text = str(result)

    # Truncate to avoid huge MCP responses (but preserve key info)
    MAX_OUTPUT = 800
    if len(output_text) > MAX_OUTPUT:
        output_text = output_text[:MAX_OUTPUT] + f"\n... [truncated, full output in memory/]"

    ci_delta = result.get("ci_delta", 0)
    ci_str = f" | CI {ci_delta:+.0f}" if ci_delta else ""

    return {
        "content": [{"type": "text", "text": f"[{status}]{ci_str}\n\n{output_text}"}],
    }
