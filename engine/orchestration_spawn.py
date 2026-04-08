"""
NEUTRON EVO OS — Orchestration Spawn Engine
True parallel N-agent execution for the orchestration skill.

This module is imported by both:
  1. mcp_server/tools.py  (via spawn_parallel wrapper)
  2. skills/core/orchestration/logic/__init__.py  (direct call in execute phase)

Provides true parallel agent spawning with timeout, error isolation,
and result collection. Uses Claude Agent SDK under the hood.
"""
from __future__ import annotations

import asyncio
import concurrent.futures
import json
import os
import tempfile
import time
from pathlib import Path
from typing import Any, Optional

try:
    from claude_agent_sdk import query, ClaudeAgentOptions
    _SDK_AVAILABLE = True
except ImportError:
    _SDK_AVAILABLE = False


# ── Config ────────────────────────────────────────────────────────────────────

NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent)
))


# ── Agent config builder ──────────────────────────────────────────────────────

def build_agent_config(
    unit: dict,
    task: str,
    spec_content: str = "",
    project_root: Optional[Path] = None,
    isolation: bool = True,
) -> dict:
    """
    Build a full agent config dict for spawn_agent().
    Mirrors the config structure expected by _spawn_agent() in tools.py.
    """
    pr = project_root or NEUTRON_ROOT
    unit_id = unit.get("id", "unit")
    unit_name = unit.get("name", unit.get("id", "Unit"))
    scope = unit.get("scope", "full")
    skills = unit.get("skills", ["workflow"])

    # Build the agent's system prompt with full context
    prompt_parts = [
        f"# Orchestration Unit: {unit_name}",
        f"## Your Task",
        f"{task}",
        f"",
        f"## Unit Scope: {scope}",
        f"## Your Responsibilities",
    ]

    for resp in unit.get("responsibilities", []):
        prompt_parts.append(f"  - {resp}")

    if spec_content:
        prompt_parts.extend([
            "",
            f"## SPEC.md (reference)",
            f"{spec_content[:2000]}",  # First 2000 chars to avoid token bloat
        ])

    # CLAUDE.md context
    claude_md = pr / ".claude" / "CLAUDE.md"
    if claude_md.exists():
        prompt_parts.extend(["", f"## Project CLAUDE.md", claude_md.read_text()[:1500]])

    # Skills to preload
    for skill in skills:
        skill_md = pr / "skills" / "core" / skill / "SKILL.md"
        if skill_md.exists():
            prompt_parts.extend(["", f"## Skill: {skill}", skill_md.read_text()[:500]])

    prompt_parts.append(f"\n# Your unit_id: {unit_id}")
    prompt_parts.append(f"Work ONLY within your unit scope. Report results clearly.")

    prompt = "\n".join(prompt_parts)

    # Choose model
    model = "claude-opus-4-5"
    agent_type = unit.get("agent", "general-purpose")
    if agent_type == "coder":
        model = "claude-sonnet-4-7"
    elif agent_type == "research":
        model = "claude-haiku-4-5"

    # Tools: base set for coding
    tools = ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]

    return {
        "agent_id": unit_id,
        "prompt": prompt,
        "model": model,
        "tools": tools,
        "cwd": str(pr),
        "env": {
            "NEUTRON_ROOT": str(pr),
            "ORCHESTRATION_UNIT": unit_id,
        },
        "max_turns": 50,
        "timeout_seconds": 600,
        "unit": unit,
    }


# ── Single agent spawn ────────────────────────────────────────────────────────

def spawn_single(config: dict) -> dict:
    """
    Spawn a single Claude Agent via Claude Agent SDK.
    Blocking call — runs until agent completes or timeout.
    """
    if not _SDK_AVAILABLE:
        return {
            "agent_id": config.get("agent_id", "?"),
            "status": "error",
            "output": "[error] claude-agent-sdk not installed. Run: pip install claude-agent-sdk",
        }

    agent_id = config.get("agent_id", "?")
    timeout = config.get("timeout_seconds", 600)
    result_parts: list[str] = []
    errors: list[str] = []

    opts = ClaudeAgentOptions(
        allowed_tools=config.get("tools", ["Read", "Bash", "Glob"]),
        cwd=config.get("cwd", os.getcwd()),
        env=config.get("env", {}),
        max_turns=config.get("max_turns", 50),
    )
    if config.get("model"):
        opts.model = config["model"]

    def _collect():
        try:
            async def _run():
                collected = []
                async for msg in query(config.get("prompt", ""), opts):
                    if hasattr(msg, "result") and msg.result:
                        collected.append(str(msg.result)[:500])
                    elif hasattr(msg, "content") and msg.content:
                        collected.append(str(msg.content)[:500])
                    elif type(msg).__name__ == "ResultMessage":
                        collected.append(str(getattr(msg, "result", "") or "")[:500])
                return collected

            result_parts.extend(asyncio.run(_run()))
        except Exception as e:
            errors.append(str(e)[:200])

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
            fut = pool.submit(_collect)
            fut.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        errors.append(f"timeout after {timeout}s")
    except Exception as e:
        errors.append(str(e)[:200])

    output = "\n".join(result_parts[-20:])
    if errors:
        output += f"\n[spawn errors: {'; '.join(errors)}]"

    MAX = 1000
    if len(output) > MAX:
        output = output[:MAX] + f"\n... [truncated, {len(output) - MAX} chars more]"

    return {
        "agent_id": agent_id,
        "status": "completed" if result_parts else ("error: " + "; ".join(errors) if errors else "no_output"),
        "output": output or "(no output)",
        "unit": config.get("unit", {}),
    }


# ── Parallel N-agent spawn ─────────────────────────────────────────────────────

def spawn_parallel_agents(unit_configs: list[dict]) -> list[dict]:
    """
    Spawn N agents in TRUE PARALLEL — all at once, not sequential.

    Each config should have: agent_id, prompt, model, tools, cwd, timeout_seconds, unit.

    Returns: list of result dicts, same order as inputs.
    Any agent that fails or times out returns an error dict (doesn't crash others).

    Usage:
        results = spawn_parallel_agents([
            {"agent_id": "unit-1", "prompt": "do X", ...},
            {"agent_id": "unit-2", "prompt": "do Y", ...},
        ])
    """
    if not unit_configs:
        return []
    if len(unit_configs) == 1:
        return [spawn_single(unit_configs[0])]

    n = len(unit_configs)
    # Per-agent timeout: overall budget divided by N, min 60s each
    per_unit_timeout = max(60, min(600, 600 // n))

    def _run_one(cfg: dict) -> dict:
        cfg = dict(cfg)  # don't mutate caller's dict
        cfg.setdefault("timeout_seconds", per_unit_timeout)
        return spawn_single(cfg)

    results: list[dict] = [None] * n

    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=n) as pool:
            futures = [pool.submit(_run_one, cfg) for cfg in unit_configs]
            for i, fut in enumerate(futures):
                try:
                    results[i] = fut.result(timeout=per_unit_timeout + 30)
                except concurrent.futures.TimeoutError:
                    results[i] = {
                        "agent_id": unit_configs[i].get("agent_id", f"unit-{i}"),
                        "status": "timeout",
                        "output": f"[agent:{unit_configs[i].get('agent_id','?')} timed out after {per_unit_timeout}s]",
                        "unit": unit_configs[i].get("unit", {}),
                    }
                except Exception as e:
                    results[i] = {
                        "agent_id": unit_configs[i].get("agent_id", f"unit-{i}"),
                        "status": "error",
                        "output": f"[agent:{unit_configs[i].get('agent_id','?')} error: {e}]",
                        "unit": unit_configs[i].get("unit", {}),
                    }
    except Exception as e:
        pass  # All results already populated

    return results
