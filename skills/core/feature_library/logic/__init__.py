"""
Feature Library Skill — Logic Module (v1.0)

route_feature(task, tech_stack, requirements) → {recommended, alternatives, reasoning, patterns}
"""
from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Optional


# Resolve paths
_SKILL_DIR = Path(__file__).parent.parent
_JSON_PATH = _SKILL_DIR / "feature_library.json"


def _load_library() -> dict:
    """Load the feature library JSON."""
    if not _JSON_PATH.exists():
        return {"categories": [], "decision_rules": []}
    try:
        return json.loads(_JSON_PATH.read_text())
    except Exception:
        return {"categories": [], "decision_rules": []}


def _normalize_stack(tech_stack: str) -> list[str]:
    """Normalize tech stack input to a list of keywords."""
    stack = tech_stack.lower().strip()
    normalized = set()

    # Map common variations
    stack_map = {
        "python": ["python", "fastapi", "django", "flask", "fastapi", "starlette"],
        "javascript": ["javascript", "node", "node.js", "express", "nest"],
        "typescript": ["typescript", "ts", "node", "express", "nest"],
        "go": ["go", "golang"],
        "rust": ["rust"],
        "java": ["java", "spring"],
        "react": ["react", "next.js", "nextjs"],
        "vue": ["vue", "nuxt", "nuxt.js"],
        "svelte": ["svelte", "sveltekit"],
    }

    for lang, keywords in stack_map.items():
        if any(k in stack for k in keywords):
            normalized.add(lang)
            if lang == "javascript":
                if "typescript" in stack or "ts" in stack:
                    normalized.add("typescript")
            if lang == "python":
                if "fastapi" in stack:
                    normalized.add("python_fastapi")
                elif "django" in stack:
                    normalized.add("python_django")

    if not normalized:
        normalized.add("any")

    return sorted(normalized)


def _score_pattern(pattern: dict, task: str, tech_stack: str, requirements: str) -> float:
    """Score a pattern (0-100) based on relevance to the project."""
    combined = f"{task} {requirements} {tech_stack}".lower()
    score = 0.0

    # Stack match (primary filter) — up to 50 points
    pattern_stacks = [s.lower() for s in pattern.get("stack", [])]
    normalized = _normalize_stack(tech_stack)

    stack_match = False
    for ns in normalized:
        # Check direct match
        if ns in pattern_stacks:
            score += 50
            stack_match = True
            break
        # Check partial (e.g., "python" pattern works for "python_fastapi")
        for ps in pattern_stacks:
            if ns.startswith(ps) or ps.startswith(ns):
                score += 40
                stack_match = True
                break
        if stack_match:
            break
        # Check "any" pattern
        if "any" in pattern_stacks:
            score += 20
            stack_match = True

    if not stack_match:
        return 0.0  # Eliminated — incompatible stack

    # Use case match — up to 30 points
    use_cases = [uc.lower() for uc in pattern.get("use_cases", [])]
    for uc in use_cases:
        if uc in combined:
            score += 10
        # Check individual words
        for word in uc.split():
            if len(word) > 3 and word in combined:
                score += 3

    # Alias match — up to 10 points
    aliases = [a.lower() for a in pattern.get("aliases", [])]
    for alias in aliases:
        if alias in combined:
            score += 5
        for word in alias.split():
            if len(word) > 3 and word in combined:
                score += 1

    # Identity/auth keyword boost — auth is usually the PRIMARY concern, not secondary
    auth_keywords = {"auth", "login", "register", "user", "account", "jwt", "oauth",
                     "password", "token", "session", "permission", "access control"}
    combined_words = set(combined.split())
    auth_in_combined = bool(auth_keywords & combined_words)

    # Check if this pattern is an auth/security pattern (has any auth keyword in aliases or use_cases)
    pattern_auth_words: set = set()
    for alias in aliases:
        pattern_auth_words.update(alias.split())
    for uc in pattern.get("use_cases", []):
        pattern_auth_words.update(uc.split())
    pattern_is_auth = bool(auth_keywords & pattern_auth_words)

    # Boost auth patterns when user explicitly mentions auth concerns
    if auth_in_combined and pattern_is_auth:
        score += 20  # Auth pattern matched → significant boost

    # Complexity penalty for large projects vs simple patterns
    project_complexity_hints = ["enterprise", "large", "complex", "microservice", "saas"]
    simple_pattern = pattern.get("complexity", "medium") == "low"
    if any(hint in combined for hint in project_complexity_hints) and simple_pattern:
        score -= 5  # Low-complexity pattern might not fit enterprise

    return min(score, 100)


def _apply_decision_rules(library: dict, task: str, requirements: str) -> list[str]:
    """Apply keyword-based decision rules to get priority pattern names."""
    combined = f"{task} {requirements}".lower()
    priority_patterns = []

    for rule in library.get("decision_rules", []):
        rule_keywords = rule.get("keywords", [])
        if not rule_keywords:
            continue
        # Check if any keyword from this rule matches
        matched = False
        for kw in rule_keywords:
            if kw.lower() in combined:
                matched = True
                break
        if matched:
            for name in rule.get("top_patterns", []):
                if name not in priority_patterns:
                    priority_patterns.append(name)

    return priority_patterns


def _build_reasoning(pattern: dict, match_reason: str, tech_stack: str) -> str:
    """Build human-readable reasoning for why this pattern was recommended."""
    reasons = []

    stack = tech_stack.lower()
    if pattern.get("stack"):
        supported = [s for s in pattern["stack"] if s.lower() in stack]
        if supported:
            reasons.append(f"Works with {', '.join(supported)}")
        elif "any" in [s.lower() for s in pattern["stack"]]:
            reasons.append("Works with any stack")

    complexity = pattern.get("complexity", "medium")
    reasons.append(f"Complexity: {complexity}")

    if match_reason:
        reasons.append(match_reason)

    tradeoffs = pattern.get("tradeoffs", "")
    if tradeoffs:
        reasons.append(f"Tradeoff: {tradeoffs[:80]}" if tradeoffs else "")

    return ". ".join(filter(None, reasons))


def route_feature(task: str, tech_stack: str = "", requirements: str = "") -> dict:
    """
    Route to the best feature patterns for a project.

    Args:
        task: Description of what the project needs
        tech_stack: Tech stack (e.g., "python fastapi", "javascript express")
        requirements: Additional requirements or context

    Returns:
        {
            "recommended": {category, pattern, reasoning, install, snippet},
            "alternatives": [...],
            "by_category": {...},
            "reasoning": str
        }
    """
    library = _load_library()
    if not library.get("categories"):
        return {"error": "Feature library not loaded", "recommended": None, "alternatives": [], "by_category": {}}

    # Apply decision rules to get priority patterns first
    rule_priority = _apply_decision_rules(library, task, requirements)

    # Score all patterns
    scored_patterns = []
    for category in library["categories"]:
        for pattern in category.get("patterns", []):
            score = _score_pattern(pattern, task, tech_stack, requirements)
            if score > 0:
                is_rule_priority = pattern["name"] in rule_priority
                scored_patterns.append({
                    "pattern": pattern,
                    "category": category,
                    "score": score + (20 if is_rule_priority else 0),  # Boost rule-matched
                    "rule_priority": is_rule_priority,
                })

    # Sort by score descending
    scored_patterns.sort(key=lambda x: x["score"], reverse=True)

    if not scored_patterns:
        return {
            "recommended": None,
            "alternatives": [],
            "by_category": {},
            "reasoning": "No patterns matched the given tech stack and requirements.",
        }

    # Top recommendation
    top = scored_patterns[0]
    best_pattern = top["pattern"]
    best_category = top["category"]

    # Get snippet for the tech stack
    snippet = ""
    normalized = _normalize_stack(tech_stack)
    impl = best_pattern.get("implementation", {})

    for ns in normalized:
        if ns in impl:
            snippet = impl[ns].get("snippet", "")
            break
    if not snippet and "python" in normalized and "python" in impl:
        snippet = impl["python"].get("snippet", "")
    if not snippet and "any" in impl:
        snippet = impl["any"].get("snippet", "")

    # Format snippet (trim to 30 lines)
    lines = snippet.split("\n")
    if len(lines) > 30:
        snippet = "\n".join(lines[:30]) + "\n    # ... (truncated)"
    else:
        snippet = "\n".join(lines)

    recommended = {
        "category": best_category["name"],
        "category_icon": best_category.get("icon", "🔧"),
        "pattern": best_pattern["name"],
        "description": best_pattern.get("description", ""),
        "complexity": best_pattern.get("complexity", "medium"),
        "reasoning": _build_reasoning(best_pattern, f"Best match for: {task[:50]}", tech_stack),
        "install": best_pattern.get("install", ""),
        "snippet": snippet,
        "when": best_pattern.get("when", ""),
        "dont_when": best_pattern.get("dont_when", ""),
        "tradeoffs": best_pattern.get("tradeoffs", ""),
        "score": top["score"],
    }

    # Alternatives (top 3 from different categories)
    alternatives = []
    seen_categories = {best_category["id"]}
    for sp in scored_patterns[1:6]:
        cat = sp["category"]
        if cat["id"] in seen_categories and len(alternatives) >= 2:
            continue
        seen_categories.add(cat["id"])
        alternatives.append({
            "category": cat["name"],
            "category_icon": cat.get("icon", "🔧"),
            "pattern": sp["pattern"]["name"],
            "description": sp["pattern"].get("description", ""),
            "complexity": sp["pattern"].get("complexity", "medium"),
            "install": sp["pattern"].get("install", ""),
            "score": sp["score"],
        })
        if len(alternatives) >= 3:
            break

    # By category breakdown
    by_category = {}
    for sp in scored_patterns[:10]:
        cat_name = sp["category"]["name"]
        if cat_name not in by_category:
            by_category[cat_name] = []
        by_category[cat_name].append({
            "pattern": sp["pattern"]["name"],
            "description": sp["pattern"].get("description", ""),
            "complexity": sp["pattern"].get("complexity", "medium"),
            "score": sp["score"],
        })

    # Summary reasoning
    reasoning_parts = [
        f"Best pattern: {best_pattern['name']} ({best_category['name']})",
        f"Tech stack match: {tech_stack or 'any'}",
    ]
    if alternatives:
        reasoning_parts.append(f"Alternatives: {', '.join(a['pattern'] for a in alternatives[:2])}")

    return {
        "recommended": recommended,
        "alternatives": alternatives,
        "by_category": by_category,
        "reasoning": ". ".join(reasoning_parts),
        "total_patterns_matched": len(scored_patterns),
    }


def route_auth(task: str, tech_stack: str = "") -> dict:
    """Route specifically to auth patterns."""
    return route_feature(task, tech_stack, requirements="auth login register user account")


def route_api(task: str, tech_stack: str = "") -> dict:
    """Route specifically to API patterns."""
    return route_feature(task, tech_stack, requirements="api endpoint rest crud server")


def get_all_patterns() -> dict:
    """Return all patterns organized by category (for reference)."""
    library = _load_library()
    return {
        cat["name"]: [
            {"name": p["name"], "description": p.get("description", ""),
             "complexity": p.get("complexity", "medium")}
            for p in cat.get("patterns", [])
        ]
        for cat in library.get("categories", [])
    }
