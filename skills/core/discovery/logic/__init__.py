"""
Discovery Skill — Logic Module
run_discovery(task, context) → {status, output, ci_delta}

Actions (via context["action"]):
  - start   : Begin discovery interview — return summary + questions
  - record  : Record user's answers, return final summary
  - status  : Check if there's an in-progress discovery

Discovery interview flow:
  start → present summary + 12 questions → user answers → record → final summary
  ↓
  OUTPUT: memory/discoveries/{date}/{slug}.md  →  used by SPEC skill
"""
from __future__ import annotations

import os
import re
import json
from pathlib import Path
from datetime import datetime

# Levels: logic/__init__.py → discovery/ → core/ → skills/ → repo root
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent.parent)
))
MEMORY_DIR = _NEUTRON_ROOT / "memory"
DISCOVERIES_DIR = MEMORY_DIR / "discoveries"
_SESSION_FILE = MEMORY_DIR / ".discovery_session.json"


# ─── Structured interview questions ────────────────────────────────────────────

INTERVIEW_QUESTIONS = [
    # Group A — Scope & Success
    {
        "id": "done_criteria",
        "group": "A — Scope & Success",
        "number": 1,
        "question": "What does 'done' look like? How will you know this is finished and working?",
        "hint": "Be specific. Not 'works well' but 'users can do X in under Y seconds with Z accuracy'.",
        "required": True,
    },
    {
        "id": "exclusions",
        "group": "A — Scope & Success",
        "number": 2,
        "question": "What should DEFINITELY NOT be built? What is out of scope?",
        "hint": "This prevents creep. Be explicit: 'No admin panel', 'No payment processing', etc.",
        "required": True,
    },
    {
        "id": "multi_user",
        "group": "A — Scope & Success",
        "number": 3,
        "question": "Is this for one person or multiple people? If multiple, do they share data or have separate accounts?",
        "hint": "Single user = simpler. Multiple users = auth, permissions, data isolation required.",
        "required": True,
    },
    # Group B — Technical Reality
    {
        "id": "tech_stack",
        "group": "B — Technical Reality",
        "number": 4,
        "question": "What technology stack do you want? (Language, framework, database, cloud/infrastructure)",
        "hint": "If you don't know, say 'I want recommendations' — I can suggest based on your goals.",
        "required": True,
    },
    {
        "id": "integrations",
        "group": "B — Technical Reality",
        "number": 5,
        "question": "Does this need to connect to existing systems? (APIs, databases, auth providers, other software)",
        "hint": "List what must integrate. 'Nothing yet' is a valid answer.",
        "required": True,
    },
    {
        "id": "ui_library",
        "group": "B — Technical Reality",
        "number": 6,
        "question": "UI library / frontend framework preference? (If frontend project)",
        "hint": "For web apps: do you have a preferred UI library?\n- No preference (I\'ll suggest the best for your project)\n- React + shadcn/ui / Ant Design / Mantine / Vue / Svelte / Other\n- DaisyUI (lightweight, Tailwind-based)\n- Magic UI (animation-heavy landing pages)\n- I\'ll build it myself (vanilla CSS/HTML)",
        "required": False,
    },
    {
        "id": "scale",
        "group": "B — Technical Reality",
        "number": 7,
        "question": "What's the expected scale? (Number of users, data volume, traffic. Or: 'just me testing for now'.)",
        "hint": "Honest answer here prevents expensive rewrites later.",
        "required": True,
    },
    # Group C — User Experience
    {
        "id": "end_users",
        "group": "C — User Experience",
        "number": 8,
        "question": "Who will actually USE this? (Technical skill level? Internal team or external customers?)",
        "hint": "A tool used by developers is different from one used by non-technical people.",
        "required": True,
    },
    {
        "id": "first_screen",
        "group": "C — User Experience",
        "number": 9,
        "question": "What does the first screen look like? Describe the main screen users see when they open the app.",
        "hint": "Words are fine. 'A login screen' or 'A dashboard showing X, Y, Z'.",
        "required": True,
    },
    {
        "id": "ui_requirements",
        "group": "C — User Experience",
        "number": 10,
        "question": "Any UI/branding requirements? (Specific colors, design system, or 'I just want it to work and look clean')",
        "hint": "Design last. Get function right first.",
        "required": False,
    },
    # Group D — Edge Cases
    {
        "id": "user_scenarios",
        "group": "D — Edge Cases",
        "number": 11,
        "question": "You mentioned [scenario] — what should happen in that case?",
        "hint": "If you already described an edge case in your prompt, expand on it here.",
        "required": False,
    },
    {
        "id": "error_handling",
        "group": "D — Edge Cases",
        "number": 12,
        "question": "What should the system do when something breaks? (Fail silently? Show error? Retry? Email you?)",
        "hint": "Error handling philosophy: 'fail fast and loud' vs 'graceful degradation'.",
        "required": True,
    },
    {
        "id": "security",
        "group": "D — Edge Cases",
        "number": 13,
        "question": "What data needs to be kept private or secure? (PII, credentials, business data?)",
        "hint": "If handling user data: GDPR considerations. If sensitive: encryption at rest.",
        "required": False,
    },
]


def _slugify(text: str) -> str:
    """Create URL-safe slug from text."""
    text = re.sub(r'[^\w\s-]', '', text.lower())
    text = re.sub(r'[-\s]+', '-', text).strip('-')
    return text[:50] or "untitled"


def _extract_from_prompt(prompt: str) -> dict:
    """
    Phase 1 analysis: extract key facts from user's raw prompt.
    Returns {what, why, who, constraints, existing_code}.
    """
    lines = [l.strip() for l in prompt.splitlines() if l.strip()]

    # Detect tech mentions
    tech_keywords = {
        "python": ["python", "django", "flask", "fastapi", "pandas"],
        "javascript": ["javascript", "node.js", "nodejs", "react", "typescript"],
        "database": ["postgresql", "postgres", "mysql", "sqlite", "mongodb", "redis"],
        "cloud": ["aws", "gcp", "azure", "docker", "kubernetes", "serverless"],
        "ai": ["openai", "anthropic", "llm", "ai", "gpt", "claude", "rag", "vector"],
    }

    detected_stack = []
    for category, keywords in tech_keywords.items():
        if any(kw in prompt.lower() for kw in keywords):
            detected_stack.append(category)

    # Detect user mentions
    user_mentions = re.findall(
        r'(?:for|to|帮|untuk|pour|para)\s+([A-Z][a-z]+(?:\s+[A-Z][a-z]+){0,3})',
        prompt
    )

    # Detect constraints
    constraint_patterns = [
        (r'\b(no|not|dont|without|exclude)\s+\w+', 'explicit exclusion'),
        (r'\bmust\s+(not\s+)?\w+', 'mandatory constraint'),
        (r'\bonly\s+\w+', 'limitation'),
    ]
    found_constraints = []
    for pattern, label in constraint_patterns:
        if re.search(pattern, prompt, re.IGNORECASE):
            found_constraints.append(label)

    return {
        "raw": prompt[:500],
        "detected_stack": detected_stack,
        "mentioned_users": user_mentions[:3],
        "constraints_found": found_constraints,
        "line_count": len(lines),
    }


def _build_summary(analysis: dict, prompt: str) -> str:
    """Build 3-sentence confirmation summary."""
    stack = ", ".join(analysis["detected_stack"]) or "any stack"
    users = analysis["mentioned_users"] or ["your users"]

    summary = (
        f"You want to build: **{prompt[:100]}...**\n"
        f"Solving for: **{', '.join(users)}**\n"
        f"Technology: **{stack}**\n"
        f"Detected constraints: **{', '.join(analysis['constraints_found']) or 'none mentioned'}**\n\n"
        f"Does this match what you mean? (YES / NO — tell me what's wrong)"
    )
    return summary


def _build_questions_text(questions: list, answers: dict) -> str:
    """Render unanswered questions as formatted text."""
    unanswered = [q for q in questions if q["required"] and q["id"] not in answers]
    optional = [q for q in questions if not q["required"] and q["id"] not in answers]

    lines = []
    for group, qs in [("A — Scope & Success", [q for q in unanswered if "A" in q["group"]]),
                       ("B — Technical Reality", [q for q in unanswered if "B" in q["group"]]),
                       ("C — User Experience", [q for q in unanswered if "C" in q["group"]]),
                       ("D — Edge Cases", [q for q in unanswered if "D" in q["group"]])]:
        if not qs:
            continue
        lines.append(f"\n### {group}\n")
        for q in qs:
            lines.append(f"**{q['number']}. {q['question']}**")
            if q.get("hint"):
                lines.append(f"   → {q['hint']}")
            lines.append("")

    if optional:
        lines.append("\n### Optional (answer if relevant)\n")
        for q in optional:
            lines.append(f"**{q['number']}. {q['question']}**")
            if q.get("hint"):
                lines.append(f"   → {q['hint']}")
            lines.append("")

    return "".join(lines)


def _save_session(slug: str, prompt: str, analysis: dict, answers: dict) -> Path:
    """Save interview session to disk for resumability."""
    DISCOVERIES_DIR.mkdir(exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    session_dir = DISCOVERIES_DIR / today / slug
    session_dir.mkdir(parents=True, exist_ok=True)

    session = {
        "slug": slug,
        "prompt": prompt,
        "analysis": analysis,
        "answers": answers,
        "updated_at": datetime.now().isoformat(),
        "status": "in_progress" if answers.get("_questions_remaining") else "complete",
    }
    path = session_dir / "session.json"
    path.write_text(json.dumps(session, indent=2, ensure_ascii=False))
    return session_dir


def _load_session() -> dict | None:
    """Load most recent in-progress session."""
    if not _SESSION_FILE.exists():
        return None
    try:
        session = json.loads(_SESSION_FILE.read_text())
        session_path = Path(session.get("session_path", ""))
        if session_path.exists():
            return json.loads(session_path.read_text())
    except Exception:
        pass
    # Fallback: find most recent
    if not DISCOVERIES_DIR.exists():
        return None
    sessions = sorted(
        DISCOVERIES_DIR.rglob("session.json"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if sessions:
        try:
            return json.loads(sessions[0].read_text())
        except Exception:
            pass
    return None


def _estimate_complexity(answers: dict) -> str:
    """Estimate project complexity based on answers."""
    score = 0
    # Multi-user
    multi_keywords = ["multiple", "multi", "team", "users", "shared", "separate accounts"]
    if any(answers.get("multi_user", "").lower().__contains__(kw) for kw in multi_keywords):
        score += 2
    # Scale
    scale_text = answers.get("scale", "").lower()
    if any(w in scale_text for w in ["100", "1000", "10000", "million", "thousand"]):
        score += 2
    if "millions" in scale_text or "high traffic" in scale_text:
        score += 3
    # Integrations
    if answers.get("integrations", "").lower() not in ("none", "nothing", "n/a", "-", ""):
        score += 2
    # Tech stack specified
    if answers.get("tech_stack", "").strip():
        score -= 1  # specified = easier
    # Security
    if answers.get("security", "").lower() not in ("none", "n/a", ""):
        score += 1
    if score <= 2:
        return "LOW"
    elif score <= 5:
        return "MEDIUM"
    else:
        return "HIGH"


def run_discovery(task: str, context: dict = None) -> dict:
    """
    Discovery interview orchestrator.

    Phase 1 (action='start'):
      - Analyze user's prompt
      - Present 3-sentence summary for confirmation
      - Present all required interview questions
      - Save session for resumability

    Phase 2 (action='record'):
      - Record user's answers
      - If all required questions answered: generate final summary + complexity
      - Write discovery output to memory/discoveries/
      - Return readiness status
    """
    context = context or {}
    action = context.get("action", "start")

    if action == "status":
        session = _load_session()
        if session:
            answered = len([a for a in session.get("answers", {}).keys() if not a.startswith("_")])
            total_required = len([q for q in INTERVIEW_QUESTIONS if q["required"]])
            remaining = total_required - answered
            return {
                "status": "in_progress",
                "project": session.get("slug", "unknown"),
                "answered": answered,
                "remaining": remaining,
                "session_path": str(session.get("_session_dir", "")),
                "ci_delta": 0,
            }
        return {"status": "no_active_session", "ci_delta": 0}

    if action == "start":
        return _start_interview(task, context)
    elif action == "record":
        return _record_answers(task, context)
    else:
        return {"status": "error", "output": f"Unknown action: '{action}'", "ci_delta": 0}


def _start_interview(task: str, context: dict) -> dict:
    """Begin the discovery interview."""
    if not task or len(task.strip()) < 5:
        return {
            "status": "error",
            "output": "Discovery requires a project idea or prompt. Please describe what you want to build.",
            "ci_delta": 0,
        }

    # Phase 1: Analyze the prompt
    analysis = _extract_from_prompt(task)
    slug = _slugify(task)
    project_name = slug.replace("-", " ").title()

    # Save/update session
    session_dir = _save_session(slug, task, analysis, {})
    _SESSION_FILE.write_text(json.dumps({
        "session_path": str(session_dir / "session.json"),
        "slug": slug,
        "started_at": datetime.now().isoformat(),
    }))

    # Build summary
    summary = _build_summary(analysis, task)
    questions_text = _build_questions_text(INTERVIEW_QUESTIONS, {})

    questions_count = len([q for q in INTERVIEW_QUESTIONS if q["required"]])

    output = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 DISCOVERY INTERVIEW — {project_name}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 1 — CONFIRM MY UNDERSTANDING:
{summary}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

STEP 2 — PLEASE ANSWER {questions_count} REQUIRED QUESTIONS:
{questions_text}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
When done, call: discovery(action='record', answers={{...}})
"""
    return {
        "status": "interview_started",
        "output": output,
        "summary_confirmed": False,
        "questions_remaining": questions_count,
        "session_path": str(session_dir),
        "slug": slug,
        "project_name": project_name,
        "ci_delta": 0,
    }


def _record_answers(task: str, context: dict) -> dict:
    """
    Record user's answers and determine if interview is complete.
    If all required questions answered → generate final summary.
    """
    session = _load_session()
    if not session:
        return {
            "status": "error",
            "output": "No active discovery session. Call discovery(action='start') first.",
            "ci_delta": 0,
        }

    new_answers = context.get("answers", {})
    slug = session["slug"]
    existing_answers = {k: v for k, v in session.get("answers", {}).items() if not k.startswith("_")}

    # Merge answers
    all_answers = {**existing_answers, **new_answers}

    # Save session
    session_dir = _save_session(slug, session["prompt"], session["analysis"], all_answers)

    # Count required unanswered
    required_questions = [q for q in INTERVIEW_QUESTIONS if q["required"]]
    unanswered_required = [q for q in required_questions if q["id"] not in all_answers]

    if unanswered_required:
        # Still have questions to answer
        remaining_text = _build_questions_text(INTERVIEW_QUESTIONS, all_answers)
        answered_count = len([a for a in all_answers.keys() if not a.startswith("_")])
        output = (
            f"📝 Recorded {len(new_answers)} answer(s). "
            f"Progress: {answered_count}/{len(required_questions)} required questions answered.\n\n"
            f"Still need answers to:\n{remaining_text}\n\n"
            f"Call discovery(action='record', answers={{...}}) when done."
        )
        return {
            "status": "answers_recorded",
            "output": output,
            "questions_remaining": len(unanswered_required),
            "session_path": str(session_dir),
            "ci_delta": 0,
        }

    # ─── All required questions answered — generate final summary ─────────
    complexity = _estimate_complexity(all_answers)

    # Generate key decisions
    key_decisions = [
        f"Stack: {all_answers.get('tech_stack', 'TBD by AI recommendation')}",
        f"Users: {all_answers.get('multi_user', 'TBD')}",
        f"Scale: {all_answers.get('scale', 'TBD')}",
        f"Integrations: {all_answers.get('integrations', 'None')}",
        f"Error handling: {all_answers.get('error_handling', 'TBD')}",
    ]

    # Top risks
    top_risks = []
    if not all_answers.get("tech_stack", "").strip():
        top_risks.append("Tech stack not confirmed — AI will recommend, user must approve")
    if not all_answers.get("done_criteria", "").strip():
        top_risks.append("'Done' criteria vague — success undefined")
    if complexity == "HIGH":
        top_risks.append("High complexity — recommend MVP scope first, expand after user review")
    if all_answers.get("integrations", "").lower() not in ("none", "nothing", "-", ""):
        top_risks.append(f"External integrations: '{all_answers.get('integrations')}' — verify API stability")

    # Generate discovery output file
    today = datetime.now().strftime("%Y-%m-%d")
    DISCOVERIES_DIR.mkdir(parents=True, exist_ok=True)
    output_dir = DISCOVERIES_DIR / today / slug
    output_dir.mkdir(parents=True, exist_ok=True)

    discovery_md = f"""# Discovery: {session['prompt'][:80]}
> Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Complexity: {complexity} | Status: READY FOR SPEC

---

## 1-Sentence Summary
{all_answers.get('done_criteria', 'TBD')}

---

## User's Original Prompt
```
{session['prompt']}
```

---

## Answers to Interview Questions

### Group A — Scope & Success

**1. What does 'done' look like?**
{all_answers.get('done_criteria', '_Not answered_')}

**2. What should NOT be built? (Exclusions)**
{all_answers.get('exclusions', '_Not specified_')}

**3. Single or multi-user?**
{all_answers.get('multi_user', '_Not specified_')}

### Group B — Technical Reality

**4. Technology stack?**
{all_answers.get('tech_stack', '_Not specified (AI will recommend)_')}

**5. External integrations?**
{all_answers.get('integrations', '_None specified_')}

**6. Expected scale?**
{all_answers.get('scale', '_Not specified_')}

### Group C — User Experience

**7. Who are the end users?**
{all_answers.get('end_users', '_Not specified_')}

**8. What does the first screen look like?**
{all_answers.get('first_screen', '_Not specified_')}

**9. UI/branding requirements?**
{all_answers.get('ui_requirements', '_Clean and functional is fine_')}

### Group D — Edge Cases

**10. Specific user scenarios?**
{all_answers.get('user_scenarios', '_Not specified_')}

**11. Error handling philosophy?**
{all_answers.get('error_handling', '_Not specified_')}

**12. Security / data privacy?**
{all_answers.get('security', '_Not specified_')}

---

## 3 Key Decisions

"""
    for i, decision in enumerate(key_decisions, 1):
        discovery_md += f"{i}. {decision}\n"

    discovery_md += f"""
## Top Risks & Assumptions

"""
    for i, risk in enumerate(top_risks, 1):
        discovery_md += f"{i}. {risk}\n"

    discovery_md += f"""
## Estimated Complexity: {complexity}

---

## Status: ✅ READY FOR SPEC

Call: `/spec` to write SPEC.md using this discovery output.
The SPEC will be submitted for USER REVIEW before any build begins.
"""

    output_path = output_dir / "DISCOVERY.md"
    output_path.write_text(discovery_md)

    # Write SPEC.md stub from discovery
    spec_path = output_dir / "SPEC.md"
    spec_path.write_text(f"""# SPEC: {session['prompt'][:80]}
> Created: {datetime.now().strftime('%Y-%m-%d %H:%M')}
> Discovery: {output_path.name} | Complexity: {complexity}
> Status: DRAFT — AWAITING USER REVIEW

---

## Problem
{all_answers.get('done_criteria', 'TBD')}

## Success Criteria
_Defined after discovery interview_

## Out of Scope
{all_answers.get('exclusions', 'TBD')}

## Users
{all_answers.get('end_users', 'TBD')}

## Tech Stack
{all_answers.get('tech_stack', 'TBD — AI will recommend')}

## Integrations
{all_answers.get('integrations', 'None')}

## Scale
{all_answers.get('scale', 'TBD')}

## First Screen
{all_answers.get('first_screen', 'TBD')}

## Error Handling
{all_answers.get('error_handling', 'TBD')}

## Security
{all_answers.get('security', 'TBD')}

## Acceptance Criteria
_For USER REVIEW — list what user will verify at acceptance test_

## Estimated Complexity: {complexity}
""")

    # Clear session
    _SESSION_FILE.unlink(missing_ok=True)

    complexity_emoji = {"LOW": "🟢", "MEDIUM": "🟡", "HIGH": "🔴"}.get(complexity, "⚪")
    output = f"""
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ DISCOVERY COMPLETE — {slug.replace('-', ' ').title()}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📁 Output: {output_path.relative_to(_NEUTRON_ROOT)}
📋 SPEC stub: {spec_path.relative_to(_NEUTRON_ROOT)}

KEY DECISIONS:
"""
    for decision in key_decisions:
        output += f"  • {decision}\n"

    output += f"""
⚠️  TOP RISKS:
"""
    for risk in top_risks:
        output += f"  • {risk}\n"

    output += f"""
{complexity_emoji} Estimated complexity: {complexity}

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
NEXT STEP: /spec — Write SPEC.md, then USER REVIEW before any build
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
    return {
        "status": "discovery_complete",
        "output": output,
        "discovery_path": str(output_path.relative_to(_NEUTRON_ROOT)),
        "spec_stub": str(spec_path.relative_to(_NEUTRON_ROOT)),
        "complexity": complexity,
        "key_decisions": key_decisions,
        "top_risks": top_risks,
        "ci_delta": 5,
    }
