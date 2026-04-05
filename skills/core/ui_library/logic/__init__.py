"""
UI Library Skill — Logic Module
route_ui_library(project_type, tech_stack, requirements) → recommendation
"""
from __future__ import annotations
from pathlib import Path
import json
import os
import re

# Levels: logic/__init__.py → ui_library/ → core/ → skills/ → repo root
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent)
))
_LIB_DATA_FILE = Path(__file__).parent.parent / "ui_libraries.json"


def _load_libs() -> dict:
    """Load ui_libraries.json."""
    if _LIB_DATA_FILE.exists():
        try:
            return json.loads(_LIB_DATA_FILE.read_text())
        except Exception:
            pass
    return {"libraries": [], "decision_rules": []}


def _normalize(text: str) -> str:
    """Lowercase + strip for matching."""
    return text.lower().strip()


def _score_library(lib: dict, project_type: str, tech_stack: str, requirements: str) -> int:
    """
    Score a library 0-100 based on how well it fits the project.
    """
    score = 0
    combined = f"{project_type} {tech_stack} {requirements}".lower()

    # Framework match — highest weight
    for stack in lib.get("stack", []):
        if stack.lower() in combined or stack.lower() in _normalize(tech_stack):
            score += 40
            break

    # Alias match
    for alias in lib.get("aliases", []):
        if alias.lower() in combined:
            score += 15

    # Use case match
    for use_case in lib.get("use_cases", []):
        if use_case.lower() in combined:
            score += 20

    # Explicit requirement keywords
    req_lower = _normalize(requirements)
    decision_rules = []

    # Landing / marketing
    if any(kw in combined for kw in ["landing", "marketing", "hero", "portfolio"]):
        if lib.get("name") in ("Magic UI", "DaisyUI", "shadcn/ui"):
            score += 15

    # Enterprise / dashboard / data-heavy
    if any(kw in combined for kw in ["enterprise", "dashboard", "admin", "B2B", "data-heavy", "CRM", "CMS"]):
        if lib["name"] in ("Ant Design", "shadcn/ui", "Mantine"):
            score += 15

    # Animation / motion / hiệu ứng
    if any(kw in req_lower for kw in ["animation", "motion", "effects", "hiệu ứng", "transitions", "visual"]):
        if lib["name"] in ("Magic UI", "Mantine", "Ant Design"):
            score += 20

    # Lightweight / performance
    if any(kw in req_lower for kw in ["lightweight", "fast", "performance", "nhẹ", "small"]):
        if lib["name"] in ("DaisyUI", "shadcn/ui"):
            score += 20

    # Customizable / tùy biến
    if any(kw in req_lower for kw in ["customize", "tùy biến", "control", "modify", "edit source"]):
        if str(lib.get("customizability", "")).startswith("HIGH"):
            score += 15

    # Form-heavy / full-featured
    if any(kw in combined for kw in ["form", "full-featured", "many components", "sẵn có"]):
        if lib["name"] in ("Ant Design", "Mantine"):
            score += 15

    return min(score, 100)


def route_ui_library(project_type: str, tech_stack: str, requirements: str = "") -> dict:
    """
    Route to the best UI library for a frontend project.

    Args:
        project_type: e.g. "landing page", "dashboard", "admin panel", "SaaS app"
        tech_stack: e.g. "next.js", "vue 3", "react", "vanilla HTML"
        requirements: e.g. "animation-heavy, modern aesthetic" or ""

    Returns:
        {
            "status": "ok",
            "recommended": {library_dict},
            "alternatives": [lib_dict, ...],
            "reasoning": str,
            "install": str,
            "repo": str
        }
    """
    if not tech_stack:
        return {
            "status": "no_stack",
            "output": "Tech stack not specified. Cannot route to UI library without knowing the framework (React, Vue, Svelte, etc.)",
            "ci_delta": 0,
        }

    libs_data = _load_libs()
    libraries = libs_data.get("libraries", [])

    if not libraries:
        return {
            "status": "error",
            "output": "UI library data not found",
            "ci_delta": 0,
        }

    # Score all libraries
    scored = []
    for lib in libraries:
        score = _score_library(lib, project_type, tech_stack, requirements)
        scored.append((score, lib))

    # Sort by score desc
    scored.sort(key=lambda x: -x[0])
    top_score = scored[0][0]

    # If top score is 0, no good match — still return the best available
    if top_score == 0:
        # Default heuristic: based on framework
        framework_lower = tech_stack.lower()
        for lib in libraries:
            for stack in lib.get("stack", []):
                if stack.lower() in framework_lower:
                    scored = [(50, lib)] + [(s, l) for s, l in scored if l != lib]
                    break

    top_lib = scored[0][1]
    top_score = scored[0][0]
    alternatives = [lib for score, lib in scored[1:5] if score > 0]

    # Generate reasoning
    reasoning_parts = []
    reasoning_parts.append(f"Framework: {tech_stack} is supported by {top_lib['name']}.")
    reasoning_parts.append(f"Use case match: {', '.join(top_lib.get('use_cases', [])[:3])}.")
    if top_lib.get("bundle"):
        reasoning_parts.append(f"Bundle: {top_lib['bundle']}.")
    if top_lib.get("customizability"):
        reasoning_parts.append(f"Customizability: {top_lib['customizability']}.")

    reasoning = " ".join(reasoning_parts)

    return {
        "status": "ok",
        "output": (
            f"**Recommended: {top_lib['name']}**\n"
            f"Reasoning: {reasoning}\n\n"
            f"📦 Install: `{top_lib.get('install', 'N/A')}`\n"
            f"🔗 Repo: {top_lib.get('repo', 'N/A')}\n"
            f"📚 Docs: {top_lib.get('docs', 'N/A')}\n"
            f"📊 Components: {top_lib.get('components_count', 'N/A')}\n\n"
            f"**Alternatives:**\n" +
            "\n".join(f"- {l.get('name', '?')} ({l.get('style', '')})" for l in alternatives[:3])
        ),
        "recommended": top_lib,
        "alternatives": alternatives[:3],
        "reasoning": reasoning,
        "install_command": top_lib.get("install", ""),
        "repo_url": top_lib.get("repo", ""),
        "docs_url": top_lib.get("docs", ""),
        "components_count": top_lib.get("components_count", ""),
        "confidence": min(top_score / 100, 1.0),
        "ci_delta": 2,
    }


def run_ui_library(task: str, context: dict = None) -> dict:
    """
    Entry point for skill_execution.run("ui_library", ...).
    Context fields: project_type, tech_stack, requirements
    """
    context = context or {}

    project_type = context.get("project_type", task)
    tech_stack = context.get("tech_stack", "")
    requirements = context.get("requirements", context.get("notes", ""))

    # If called with a user prompt, try to extract info
    if not tech_stack:
        # Try to extract from task string
        combined = _normalize(task)
        for lib in _load_libs().get("libraries", []):
            for alias in lib.get("aliases", []):
                if alias.lower() in combined:
                    # Found library mentioned — use it
                    return {
                        "status": "ok",
                        "output": (
                            f"You mentioned {lib['name']} — that's a great choice.\n"
                            f"Repo: {lib.get('repo', '')}\n"
                            f"Install: `{lib.get('install', '')}`\n"
                            f"When: {lib.get('when', '')}\n"
                            f"Don't when: {lib.get('dont_when', '')}"
                        ),
                        "recommended": lib,
                        "ci_delta": 1,
                    }
        # No library found in prompt
        return {
            "status": "needs_info",
            "output": (
                "I need more info to suggest a UI library:\n\n"
                "What framework are you using?\n"
                "- React / Next.js\n"
                "- Vue / Nuxt\n"
                "- Svelte\n"
                "- Vanilla HTML / other\n\n"
                "And what type of project?\n"
                "- Landing page / marketing\n"
                "- Dashboard / admin\n"
                "- SaaS app\n"
                "- Enterprise\n\n"
                "Call: ui_library(task, {\"tech_stack\": \"next.js\", \"project_type\": \"dashboard\"})"
            ),
            "ci_delta": 0,
        }

    return route_ui_library(project_type, tech_stack, requirements)
