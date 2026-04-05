"""
SPEC Debate Skill — Logic Module (v1.0)

run_spec_skill(task, context) → {status, output, rounds, next_action}

Rounds:
  prepare      : Load discovery, check LEARNED.md warnings, generate questions
  round1       : Assumption challenge — 5+ questions, minimum 5 answered
  round2       : Edge case hunt — 3+ scenarios resolved
  round3       : Write SPEC.md with hardened requirements
  approve      : User approves/changes/abandons SPEC (also writes workflow gate)
  revise       : User requested changes → rewrite SPEC

State stored in: memory/.spec_debate_state.json
Workflow gate:  memory/.workflow_gate.json (written on approve)
"""
from __future__ import annotations

import filelock
import json
import os
import re
import tempfile
from pathlib import Path
from datetime import datetime

from engine._atomic import atomic_write

# Resolve NEUTRON_ROOT from environment or this file's location
_NEUTRON_ROOT = Path(os.environ.get(
    "NEUTRON_ROOT",
    str(Path(__file__).parent.parent.parent.parent)
))
MEMORY_DIR = _NEUTRON_ROOT / "memory"
_STATE_FILE = MEMORY_DIR / ".spec_debate_state.json"
_WORKFLOW_GATE_FILE = MEMORY_DIR / ".workflow_gate.json"


# ─── Workflow Gate Helpers (shared with workflow skill) ────────────────────────

def _load_workflow_gate() -> dict:
    """Load workflow gate state — mirrors workflow skill's _load_gate()."""
    if _WORKFLOW_GATE_FILE.exists():
        try:
            return json.loads(_WORKFLOW_GATE_FILE.read_text())
        except Exception:
            pass
    return {"spec_approved": False, "acceptance_passed": False, "current_step": None}


def _save_workflow_gate(state: dict) -> None:
    """Save workflow gate state atomically with filelock."""
    MEMORY_DIR.mkdir(exist_ok=True)
    lock = filelock.FileLock(str(_WORKFLOW_GATE_FILE.with_suffix(".lock")), timeout=10)
    try:
        with lock:
            atomic_write(_WORKFLOW_GATE_FILE, json.dumps(state, indent=2))
    except filelock.Timeout:
        raise RuntimeError("Lock timeout on workflow gate")


# ─── State Management ──────────────────────────────────────────────────────────

def _load_state() -> dict:
    if _STATE_FILE.exists():
        try:
            return json.loads(_STATE_FILE.read_text())
        except Exception:
            pass
    return {"round": "prepare", "answers": {}, "edge_cases": [], "spec_written": False}


def _save_state(state: dict) -> None:
    """Save SPEC debate state atomically with filelock."""
    MEMORY_DIR.mkdir(exist_ok=True)
    lock = filelock.FileLock(str(_STATE_FILE.with_suffix(".lock")), timeout=10)
    try:
        with lock:
            atomic_write(_STATE_FILE, json.dumps(state, indent=2))
    except filelock.Timeout:
        raise RuntimeError("Lock timeout on SPEC debate state")


def _clear_state() -> None:
    try:
        _STATE_FILE.unlink(missing_ok=True)
    except OSError:
        pass


# ─── Discovery Output Loader ──────────────────────────────────────────────────

def _load_discovery_output() -> dict | None:
    """Find and load the most recent DISCOVERY.md."""
    candidates = (
        list(_NEUTRON_ROOT.glob("DISCOVERY.md"))
        + list(MEMORY_DIR.rglob("DISCOVERY.md"))
    )
    for p in sorted(candidates, key=lambda f: (f.stat().st_mtime, str(f)), reverse=True):
        try:
            content = p.read_text()
            # Verify it's a real discovery (has structured fields)
            if any(marker in content for marker in ["## ", "UNDERSTOOD", "Summary", "Questions"]):
                return {"path": str(p.relative_to(_NEUTRON_ROOT)), "content": content}
        except Exception:
            continue
    return None


# ─── LEARNED.md Warning Check ─────────────────────────────────────────────────

def _check_learned_warnings(task: str, discovery_content: str) -> list[dict]:
    """
    Search LEARNED.md for bugs relevant to this project.

    Searches BOTH section headers (## Bug: ...) AND body content.
    Also searches #tag markers embedded in entries.

    This ensures that buried bug descriptions are found, not just titles.
    """
    learned_path = MEMORY_DIR / "LEARNED.md"
    if not learned_path.exists():
        return []

    content = learned_path.read_text()

    # Keywords to match based on task + discovery
    keywords = _extract_keywords(task, discovery_content)
    if not keywords:
        return []

    warnings = []
    lines = content.split("\n")

    # Strategy: find all ## [...] blocks, search both header AND body
    current_block: list[str] = []
    current_title = ""

    for line in lines:
        if line.startswith("## [") and any(
            tag in line for tag in ["Bug:", "Issue:", "Gotcha:", "Pitfall:", "Fix:", "Lesson:"]
        ):
            # Process previous block
            if current_block and current_title:
                block_text = "\n".join(current_block).lower()
                matched_keywords = [k for k in keywords if k in block_text]
                if matched_keywords:
                    # Check if body (not just title) matched
                    body_only = "\n".join(current_block[1:]).lower()
                    if any(k in body_only for k in matched_keywords):
                        snippet = "\n".join(current_block[:8])
                        warnings.append({
                            "title": current_title.strip(),
                            "matched_keywords": matched_keywords,
                            "snippet": snippet[:300],
                        })
            # Start new block
            current_block = [line]
            current_title = line
        elif current_block is not None:
            current_block.append(line)

    # Don't forget last block
    if current_block and current_title:
        block_text = "\n".join(current_block).lower()
        matched_keywords = [k for k in keywords if k in block_text]
        if matched_keywords:
            body_only = "\n".join(current_block[1:]).lower()
            if any(k in body_only for k in matched_keywords):
                snippet = "\n".join(current_block[:8])
                warnings.append({
                    "title": current_title.strip(),
                    "matched_keywords": matched_keywords,
                    "snippet": snippet[:300],
                })

    return warnings[:3]  # Max 3 warnings


def _extract_keywords(task: str, discovery_content: str) -> list[str]:
    """Extract meaningful keywords from task + discovery for LEARNED.md search."""
    combined = (task + " " + discovery_content).lower()
    # Extract words 4+ chars, excluding common stopwords
    stopwords = {
        "the", "and", "for", "that", "with", "this", "from", "have", "has",
        "will", "would", "could", "should", "what", "when", "where", "which",
        "user", "users", "need", "want", "like", "want", "also", "just",
        "does", "doesnt", "cant", "wont", "dont", "need", "must", "make",
        "build", "using", "using", "based", "into", "than", "then", "when",
        "about", "after", "before", "between", "system", "application",
        "project", "feature", "features", "component", "components",
    }
    words = re.findall(r"[a-z]{4,}", combined)
    return sorted(set(words) - stopwords)[:8]


# ─── Round 1: Assumption Challenge ─────────────────────────────────────────

def _generate_round1_questions(discovery_content: str, task: str) -> list[str]:
    """Generate 5 targeted assumption questions based on discovery output."""
    q = []
    disc_lower = discovery_content.lower() + task.lower()

    # Tech stack detection
    has_frontend = any(k in disc_lower for k in ["react", "vue", "svelte", "angular", "next", "nuxt", "frontend", "ui", "web app"])
    has_backend = any(k in disc_lower for k in ["api", "server", "backend", "node", "django", "fastapi", "flask", "express"])
    has_db = any(k in disc_lower for k in ["database", "postgres", "mysql", "mongodb", "sqlite", "redis", "sql"])
    has_auth = any(k in disc_lower for k in ["auth", "login", "register", "user", "account", "password", "jwt", "oauth"])
    has_file = any(k in disc_lower for k in ["upload", "file", "image", "video", "media", "import", "export"])
    has_payment = any(k in disc_lower for k in ["payment", "stripe", "billing", "subscription", "pricing", "plan"])
    has_realtime = any(k in disc_lower for k in ["realtime", "websocket", "live", "stream", "notification", "push"])
    has_mobile = any(k in disc_lower for k in ["mobile", "ios", "android", "react native", "flutter"])

    # Core questions (always relevant)
    q.append(
        "**Scale:** You mentioned [feature]. What happens if 100+ users try it at the same time? "
        "Is there a concurrency concern?"
    )

    # Data/state questions
    if has_db or has_backend:
        q.append(
            "**Data integrity:** If [action] fails halfway through, should partial data be rolled back? "
            "Or is partial state acceptable?"
        )

    # Auth questions
    if not has_auth:
        q.append(
            "**Authentication:** You didn't mention login/accounts. "
            "Does the app need user identity, or is it anonymous/public?"
        )
    else:
        q.append(
            "**Session expiry:** What happens if a logged-in user's session expires in the middle of [action]? "
            "Show error? Redirect to login? Auto-refresh?"
        )

    # File/media questions
    if has_file:
        q.append(
            "**File handling:** What if a user uploads a file that's too large, wrong format, or corrupt? "
            "What error should they see?"
        )
        q.append(
            "**File storage:** Where do uploaded files live — local disk, cloud storage (S3/GCS)? "
            "Who manages storage costs?"
        )

    # Payment questions
    if has_payment:
        q.append(
            "**Payment failure:** What if payment charges successfully but the confirmation/receipt fails? "
            "Does the user get access? Is their money taken? How do they recover?"
        )
        q.append(
            "**Refund/cancellation:** What's the policy? Immediate or grace period? "
            "Who handles disputes?"
        )

    # Real-time questions
    if has_realtime:
        q.append(
            "**Reconnection:** If a user's realtime connection drops, "
            "do they need to re-authenticate? "
            "Do they see a 'reconnecting...' state? How long do you wait?"
        )

    # Mobile questions
    if has_mobile:
        q.append(
            "**Mobile offline:** Does [feature] work offline? "
            "Or does it gracefully degrade with a 'requires internet' message?"
        )

    # Frontend questions
    if has_frontend:
        q.append(
            "**Browser support:** Which browsers must be supported? "
            "Old IE? Safari iOS only? Does [feature] work the same on all browsers?"
        )

    # API/integration questions
    if has_backend and not has_payment:
        q.append(
            "**API contracts:** If this app exposes an API, "
            "what happens to clients when you change the API structure? "
            "Versioning strategy?"
        )

    # Security baseline
    q.append(
        "**Security baseline:** Is there any data that should NEVER be logged, "
        "even in error reports? "
        "(e.g., PII, passwords, tokens, financial data)"
    )

    # Return 6 most targeted questions
    return q[:6]


# ─── Round 2: Edge Case Generation ───────────────────────────────────────────

def _generate_edge_cases(discovery_content: str, task: str, round1_answers: dict) -> list[dict]:
    """Generate 4-5 specific edge case scenarios based on tech stack + answers."""
    disc_lower = (discovery_content + " " + task).lower()
    scenarios = []

    # Detect what kind of system this is
    has_api = any(k in disc_lower for k in ["api", "rest", "endpoint", "http", "server", "backend"])
    has_frontend = any(k in disc_lower for k in ["react", "vue", "svelte", "next", "nuxt", "web app"])
    has_db = any(k in disc_lower for k in ["database", "postgres", "mysql", "mongodb", "sqlite", "data store"])
    has_auth = any(k in disc_lower for k in ["auth", "login", "register", "user", "account", "jwt"])
    has_upload = any(k in disc_lower for k in ["upload", "file", "import", "media"])
    has_payment = any(k in disc_lower for k in ["payment", "stripe", "billing", "pricing", "subscription"])
    has_realtime = any(k in disc_lower for k in ["realtime", "websocket", "live", "notification", "push"])
    has_crud = any(k in disc_lower for k in ["crud", "create", "read", "update", "delete", "table", "form"])

    # API failure scenarios
    if has_api:
        scenarios.append({
            "id": "api_down",
            "scenario": "External API returns 503 Service Unavailable",
            "questions": [
                "Does the app show an error message to the user?",
                "Does it retry automatically? How many times?",
                "Is partial data shown if available?",
            ],
        })
        scenarios.append({
            "id": "api_timeout",
            "scenario": "API request times out (>30 seconds)",
            "questions": [
                "How does the UI indicate the timeout?",
                "Does the user see a 'try again' button?",
                "Is the operation logged for debugging?",
            ],
        })

    # Auth edge cases
    if has_auth:
        scenarios.append({
            "id": "session_mid_action",
            "scenario": "User's session expires while filling out a form",
            "questions": [
                "Does the form data get preserved?",
                "Does the user get redirected to login?",
                "Do they lose their input?",
            ],
        })
        scenarios.append({
            "id": "concurrent_login",
            "scenario": "User logs in from two devices simultaneously",
            "questions": [
                "Is this allowed? Or does the second login invalidate the first?",
                "Does the user see both sessions?",
                "Is there a session limit per account?",
            ],
        })

    # File upload edge cases
    if has_upload:
        scenarios.append({
            "id": "invalid_file",
            "scenario": "User uploads a file that's too large / wrong MIME type / corrupt",
            "questions": [
                "Validation happens client-side, server-side, or both?",
                "What's the exact error message?",
                "Is the file partially uploaded before rejection?",
            ],
        })

    # Payment edge cases
    if has_payment:
        scenarios.append({
            "id": "payment_inconsistency",
            "scenario": "Payment charges successfully but the app doesn't receive the confirmation",
            "questions": [
                "Does the user get access?",
                "Is this reconciled automatically (webhook retry)?",
                "How long does reconciliation take?",
            ],
        })

    # Real-time edge cases
    if has_realtime:
        scenarios.append({
            "id": "realtime_disconnect",
            "scenario": "User's realtime connection drops for 30 seconds during a live update",
            "questions": [
                "Do they see a 'reconnecting...' indicator?",
                "When they reconnect, do they get a full state refresh?",
                "Is data from the disconnected period lost or queued?",
            ],
        })

    # CRUD data scenarios
    if has_crud and has_db:
        scenarios.append({
            "id": "duplicate_submit",
            "scenario": "User clicks 'Submit' twice in rapid succession (race condition)",
            "questions": [
                "Does the app create two records or one?",
                "Is there deduplication by unique key?",
                "Does the UI prevent double-click?",
            ],
        })

    # Generic fallback edge case
    if not scenarios:
        scenarios.append({
            "id": "generic_error",
            "scenario": "An unexpected error occurs (unhandled exception in production)",
            "questions": [
                "Does the app crash or show a graceful error?",
                "Is the error logged with enough context to debug?",
                "Does the user see technical details or a friendly message?",
            ],
        })

    return scenarios[:5]  # Max 5


# ─── SPEC.md Writer ──────────────────────────────────────────────────────────

def _build_spec_content(
    task: str,
    discovery: dict | None,
    round1_answers: dict,
    resolved_edge_cases: list[dict],
    ui_library_result: dict | None,
) -> str:
    """Build the full SPEC.md content."""
    lines = []
    lines.append(f"# SPEC.md — {task.strip()}")
    lines.append(f"\n*Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}*")
    lines.append(f"*AI Gatekeeper: Claude Opus (Debate-hardened via 3-round adversarial loop)*")

    # Problem Statement
    lines.append("\n## 1. Problem Statement")
    if discovery and discovery.get("content"):
        # Try to extract problem statement from discovery
        content = discovery["content"]
        summary_match = re.search(r"UNDERSTOOD[:\s]+(.{50,500})", content, re.IGNORECASE)
        if summary_match:
            lines.append(f"\n{summary_match.group(1).strip()}")
        else:
            lines.append(f"\nFrom discovery: {task.strip()}")
    else:
        lines.append(f"\n{task.strip()}")

    # Success Criteria
    lines.append("\n## 2. Success Criteria (Measurable)")
    criteria = _derive_success_criteria(task, discovery, round1_answers, resolved_edge_cases)
    for i, c in enumerate(criteria, 1):
        lines.append(f"- [ ] {i}. {c}")

    # Tech Stack
    lines.append("\n## 3. Tech Stack")
    tech_lines = _derive_tech_stack(task, discovery)
    lines.extend(tech_lines)

    # Feature patterns (backend/API patterns auto-suggested)
    feature_patterns = _suggest_feature_patterns(task, tech_lines)
    if feature_patterns:
        lines.append("\n### Recommended Patterns")
        for fp in feature_patterns:
            lines.append(f"- **{fp['category_icon']} {fp['pattern']}** ({fp['category']}): {fp['reasoning']}")
            if fp.get("install"):
                lines.append(f"  - Install: `{fp['install']}`")
            if fp.get("when"):
                lines.append(f"  - Use when: {fp['when']}")

    if ui_library_result:
        lines.append(f"\n### UI Library")
        lines.append(f"- **Library:** {ui_library_result.get('recommended', 'Not specified')}")
        if ui_library_result.get("install"):
            lines.append(f"- **Install:** `{ui_library_result['install']}`")
        if ui_library_result.get("alternatives"):
            lines.append(f"- **Alternatives:** {', '.join(ui_library_result['alternatives'])}")

    # Out of Scope
    lines.append("\n## 4. Out of Scope")
    lines.append("What will NOT be built:")
    scope_items = _derive_out_of_scope(task, discovery)
    for item in scope_items:
        lines.append(f"- ❌ {item}")

    # Functionality
    lines.append("\n## 5. Functionality Specification")
    lines.append("\n### Core Features")
    lines.append("| Feature | Description | Priority |")
    lines.append("|---------|-------------|---------|")
    features = _derive_features(task, discovery)
    for f_id, f_name, f_desc in features:
        lines.append(f"| **{f_id}** | {f_desc} | MUST |")

    # Data model
    lines.append("\n### Data Model")
    lines.append("| Entity | Fields | Notes |")
    lines.append("|--------|--------|-------|")
    entities = _derive_data_model(task, discovery)
    for entity, fields, notes in entities:
        lines.append(f"| {entity} | {fields} | {notes} |")

    # API endpoints (if backend)
    disc_lower = ((discovery.get("content", "") if discovery else "") + " " + task).lower()
    if any(k in disc_lower for k in ["api", "endpoint", "server", "backend", "http"]):
        lines.append("\n### API Endpoints")
        lines.append("| Method | Path | Input | Output | Error |")
        lines.append("|--------|------|-------|--------|-------|")
        lines.append("| GET | /api/health | — | `200 OK` | — |")
        lines.append("| POST | /api/... | JSON | JSON | `400/401/500` |")

    # Edge Cases
    lines.append("\n### Edge Cases (Resolved from Round 2)")
    lines.append("| Scenario | Resolution |")
    lines.append("|----------|------------|")
    for ec in resolved_edge_cases:
        resolution = ec.get("resolution", "See scenario description")
        lines.append(f"| {ec.get('scenario', 'N/A')} | {resolution} |")

    # Open Questions (from Round 1)
    lines.append("\n## 6. Open Questions (Answered in Round 1)")
    lines.append("| Question | Answer |")
    lines.append("|----------|--------|")
    for q, a in round1_answers.items():
        if a and str(a).lower() not in ("skip", "n/a", "not applicable", "unknown"):
            short_q = q[:70] + "..." if len(q) > 70 else q
            short_a = str(a)[:60] + "..." if len(str(a)) > 60 else str(a)
            lines.append(f"| {short_q} | {short_a} |")

    # User Acceptance Criteria
    lines.append("\n## 7. User Acceptance Criteria")
    lines.append("*(Checkboxes the USER runs through during acceptance test)*")
    acceptance = _derive_acceptance_criteria(criteria)
    for c in acceptance:
        lines.append(f"- [ ] {c}")

    # File Structure
    lines.append("\n## 8. File Structure")
    lines.append("```")
    lines.append(f"{_derive_file_structure(task, discovery)}")
    lines.append("```")

    return "\n".join(lines)


def _suggest_feature_patterns(task: str, tech_lines: list[str]) -> list[dict]:
    """Auto-suggest feature library patterns based on task + tech stack."""
    try:
        from skills.core.feature_library.logic import route_feature

        tech_stack = ""
        for line in tech_lines:
            if "Languages" in line or "Framework" in line:
                tech_stack = line.split("**")[-1].strip()
                break

        result = route_feature(task, tech_stack=tech_stack, requirements="")

        recommendations = []
        if result.get("recommended"):
            recommendations.append(result["recommended"])
        for alt in result.get("alternatives", [])[:2]:
            if len(recommendations) < 3:
                recommendations.append(alt)

        return recommendations
    except Exception:
        return []


def _derive_success_criteria(task, discovery, answers, edge_cases) -> list[str]:
    """Infer concrete success criteria from task + discovery + answers."""
    criteria = []
    disc_lower = ((discovery.get("content", "") if discovery else "") + " " + task).lower()

    # Generic baseline criteria
    criteria.append("App loads without errors in target environment")
    criteria.append("All user-facing features are functional and return expected results")
    criteria.append("Error states show user-friendly messages (no raw stack traces)")

    if any(k in disc_lower for k in ["api", "server", "endpoint"]):
        criteria.append("All API endpoints return correct HTTP status codes")
        criteria.append("API responses match documented format")

    if any(k in disc_lower for k in ["database", "data", "crud", "form"]):
        criteria.append("Data persists correctly between sessions (create + read)")
        criteria.append("Invalid input is rejected with descriptive error messages")

    if any(k in disc_lower for k in ["auth", "login", "user"]):
        criteria.append("Authenticated users can access protected features")
        criteria.append("Unauthenticated users are redirected to login")
        criteria.append("Session expiry behaves as specified")

    if any(k in disc_lower for k in ["file", "upload", "import"]):
        criteria.append("Valid files are accepted and processed")
        criteria.append("Invalid files are rejected with user-visible error")

    if any(k in disc_lower for k in ["payment", "pricing", "subscription"]):
        criteria.append("Payment flow completes without double-charging")
        criteria.append("Failed payments show clear error and allow retry")

    # Add from edge cases
    for ec in edge_cases:
        resolution = ec.get("resolution", "")
        if resolution:
            criteria.append(f"Edge case '{ec.get('scenario', '')[:50]}' handled per spec")

    return criteria[:8]


def _derive_tech_stack(task, discovery) -> list[str]:
    """Infer tech stack from task + discovery."""
    lines = []
    disc_lower = ((discovery.get("content", "") if discovery else "") + " " + task).lower()

    stack_keywords = {
        "python": ["python", "django", "fastapi", "flask"],
        "javascript": ["node", "express", "javascript", "typescript", "js"],
        "react": ["react", "next.js", "nextjs", "react native"],
        "vue": ["vue", "nuxt", "nuxt.js"],
        "svelte": ["svelte", "sveltekit"],
        "postgres": ["postgres", "postgresql"],
        "mysql": ["mysql", "mariadb"],
        "mongodb": ["mongodb", "mongo"],
        "sqlite": ["sqlite"],
    }

    detected = []
    for stack_name, keywords in stack_keywords.items():
        if any(k in disc_lower for k in keywords):
            detected.append(stack_name.title())

    if detected:
        lines.append(f"- **Languages/Frameworks:** {', '.join(detected)}")
    else:
        lines.append("- **Languages/Frameworks:** [To be confirmed]")

    lines.append("- **Infrastructure:** [To be confirmed]")
    return lines


def _derive_out_of_scope(task, discovery) -> list[str]:
    disc_lower = ((discovery.get("content", "") if discovery else "") + " " + task).lower()
    excluded = []
    if any(k in disc_lower for k in ["landing", "marketing", "blog"]):
        excluded.append("Admin dashboard (v1)")
    if any(k in disc_lower for k in ["app", "mobile", "ios", "android"]):
        excluded.append("Web version (v1)")
    if any(k in disc_lower for k in ["api", "server"]):
        excluded.append("Native mobile SDK")
    excluded.append("Multi-tenancy (v1 is single-tenant)")
    excluded.append("Admin panel / CMS")
    return excluded[:5]


def _derive_features(task, discovery) -> list[tuple]:
    disc_lower = ((discovery.get("content", "") if discovery else "") + " " + task).lower()
    features = []

    if any(k in disc_lower for k in ["auth", "login", "register", "user"]):
        features.append(("F1", "Authentication", "Login / register / logout flow"))
    if any(k in disc_lower for k in ["crud", "create", "read", "update", "delete", "table", "form"]):
        features.append(("F2", "Data CRUD", "Create, read, update, delete operations on core entities"))
    if any(k in disc_lower for k in ["api", "endpoint", "rest"]):
        features.append(("F3", "API", "REST API endpoints with proper error handling"))
    if any(k in disc_lower for k in ["dashboard", "analytics", "chart"]):
        features.append(("F4", "Dashboard", "Overview dashboard with key metrics"))
    if any(k in disc_lower for k in ["notification", "email", "push"]):
        features.append(("F5", "Notifications", "Alert/notification system"))

    if not features:
        features.append(("F1", "Core Feature", "Primary functionality as described"))

    return features[:6]


def _derive_data_model(task, discovery) -> list[tuple]:
    disc_lower = ((discovery.get("content", "") if discovery else "") + " " + task).lower()
    entities = []

    if any(k in disc_lower for k in ["auth", "user", "account", "login"]):
        entities.append(("User", "id, email, password_hash, created_at", "Auth source of truth"))
    if any(k in disc_lower for k in ["crud", "data", "post", "item", "product"]):
        entities.append(("Item", "id, title, description, created_at, user_id", "Core entity"))
    if any(k in disc_lower for k in ["api", "endpoint"]):
        entities.append(("APIKey", "id, key_hash, user_id, created_at, last_used", "Rate limiting"))

    if not entities:
        entities.append(("Item", "id, name, data, created_at", "Core data entity"))

    return entities[:4]


def _derive_acceptance_criteria(success_criteria: list[str]) -> list[str]:
    """Convert success criteria to user-facing acceptance criteria."""
    return [c.replace("- [ ] ", "") for c in success_criteria[:6]]


def _derive_file_structure(task, discovery) -> str:
    disc_lower = ((discovery.get("content", "") if discovery else "") + " " + task).lower()

    if any(k in disc_lower for k in ["python", "fastapi", "django", "flask"]):
        return (
            "/\n"
            "├── main.py\n"
            "├── requirements.txt\n"
            "├── .env.example\n"
            "├── app/\n"
            "│   ├── __init__.py\n"
            "│   ├── routes/\n"
            "│   ├── models/\n"
            "│   └── utils/\n"
            "└── tests/\n"
        )
    elif any(k in disc_lower for k in ["react", "vue", "svelte", "next", "nuxt"]):
        return (
            "/\n"
            "├── package.json\n"
            "├── src/\n"
            "│   ├── App.tsx\n"
            "│   ├── components/\n"
            "│   ├── pages/\n"
            "│   └── utils/\n"
            "└── tests/\n"
        )
    else:
        return "/\n├── src/\n├── tests/\n└── config/\n"


# ─── UI Library Router ───────────────────────────────────────────────────────

def _check_ui_library(task: str, discovery_content: str) -> dict | None:
    """Check if project is frontend and route to UI library."""
    disc_lower = (discovery_content + " " + task).lower()
    frontend_keywords = [
        "react", "vue", "svelte", "angular", "next", "nuxt",
        "frontend", "web app", "website", "landing", "dashboard",
        "ui", "user interface", "component"
    ]

    if not any(k in disc_lower for k in frontend_keywords):
        return None

    try:
        from skills.core.ui_library.logic import route_ui_library

        # Try to extract project type and requirements from discovery
        req = ""
        if discovery_content:
            # Get first 200 chars of discovery as requirements hint
            req = discovery_content[:200]

        result = route_ui_library(
            project_type="web app",
            tech_stack=_detect_frontend_stack(task, discovery_content),
            requirements=req,
        )
        return result
    except Exception:
        return None


def _detect_frontend_stack(task: str, discovery: str) -> str:
    disc_lower = (discovery + " " + task).lower()
    if "next" in disc_lower or "next.js" in disc_lower:
        return "next.js"
    if "nuxt" in disc_lower or "nuxt.js" in disc_lower:
        return "vue"
    if "react" in disc_lower:
        return "react"
    if "vue" in disc_lower:
        return "vue"
    if "svelte" in disc_lower:
        return "svelte"
    return "react"  # safe default


# ─── SPEC Lint ────────────────────────────────────────────────────────────────

def _lint_spec(spec_content: str) -> list[str]:
    """Check SPEC.md for common problems."""
    issues = []
    lines = spec_content.split("\n")

    # Check for vague criteria
    for i, line in enumerate(lines):
        if line.strip().startswith("- [ ]"):
            text = line.lower()
            if any(vague in text for vague in ["works well", "good", "fast", "nice", "user friendly"]):
                if "error" not in text and "within" not in text:
                    issues.append(f"Line {i+1}: Criterion may be too vague: '{line.strip()[:60]}'")

    # Check for missing sections
    required_sections = ["Problem Statement", "Success Criteria", "Tech Stack", "Functionality"]
    for req in required_sections:
        if req not in spec_content:
            issues.append(f"Missing section: {req}")

    # Check acceptance criteria exist
    if "Acceptance Criteria" not in spec_content:
        issues.append("Missing: User Acceptance Criteria section")

    return issues


# ─── Main Entry Point ─────────────────────────────────────────────────────────

def run_spec_skill(task: str, context: dict = None) -> dict:
    """
    Main entry point for the SPEC Debate Skill.

    Actions (via context["action"]):
      prepare    : Load discovery, prepare questions (default)
      round1     : User answered Round 1 questions
      round2     : User resolved Round 2 edge cases
      write      : Write SPEC.md (called before approval gate)
      approve    : User approved SPEC
      revise     : User requested changes

    Returns dict with status, output text, and routing info.
    """
    context = context or {}
    action = context.get("action", "prepare")
    state = _load_state()

    # ── PREPARE: Load inputs ─────────────────────────────────────────────────
    if action == "prepare":
        # Guard: if a debate is already in progress, resume from current round
        # instead of restarting (prevents stale state + duplicate questions)
        existing_round = state.get("round", "")
        existing_task = state.get("task", "")
        if existing_round in ("round1", "round2", "write"):
            # Resume from where we left off
            if existing_round == "round1":
                round_num = 1
            elif existing_round == "round2":
                round_num = 2
            else:
                round_num = 3
            return {
                "status": "debate_in_progress",
                "output": (
                    f"⚠️  SPEC debate already in progress (Round {round_num}).\n\n"
                    f"Task: {existing_task[:60]}\n"
                    f"Current round: {existing_round}\n\n"
                    "Answer the questions above or type 'continue' to proceed."
                ),
                "round": existing_round,
                "next_action": existing_round,
                "debate_in_progress": True,
                "ci_delta": 0,
            }

        discovery = _load_discovery_output()
        discovery_content = (discovery or {}).get("content", "")
        warnings = _check_learned_warnings(task, discovery_content)

        # Round 1 questions
        questions = _generate_round1_questions(discovery_content, task)
        questions_text = "\n".join(f"{i+1}. {q}" for i, q in enumerate(questions))

        # Round 2 prep (will be generated after round 1 answers)
        state.update({
            "task": task,
            "discovery_path": discovery.get("path") if discovery else None,
            "discovery_content": discovery_content,
            "warnings": warnings,
            "round": "round1",
            "round1_questions": questions,
        })
        _save_state(state)

        # Build output
        output_parts = []

        if warnings:
            output_parts.append("⚠️  PAST BUG ALERT — Similar issues recorded in LEARNED.md:")
            for w in warnings:
                output_parts.append(f"\n   {w['title']}")
                output_parts.append(f"   {w['snippet'][:150]}")
            output_parts.append("\n   → I'll design around these. If I'm wrong, correct me in Round 1.\n")

        output_parts.append("""
╔══════════════════════════════════════════════════════════╗
║  ROUND 1: ASSUMPTION CHALLENGE                          ║
║                                                          ║
║  Before writing SPEC, I challenge what was assumed.     ║
║  Answer what you know. Say "skip" for what doesn't apply║
║  — but every skip is a risk I won't know about.         ║
║                                                          ║
║  Questions (answer with number + your answer):          ║
╚══════════════════════════════════════════════════════════╝
""")
        output_parts.append(questions_text)

        return {
            "status": "round1_ready",
            "output": "\n".join(output_parts),
            "next_action": "round1",
            "round": 1,
            "warnings": warnings,
            "discovery_path": discovery.get("path") if discovery else None,
            "ci_delta": 0,
        }

    # ── ROUND 1: Process answers ─────────────────────────────────────────────
    elif action == "round1":
        answers = context.get("answers", {})

        # Store answers in state
        state["round1_answers"] = answers
        state["round"] = "round2"
        _save_state(state)

        discovery_content = state.get("discovery_content", "")
        task = state.get("task", task)

        # Generate edge cases based on tech stack + answers
        edge_cases = _generate_edge_cases(discovery_content, task, answers)
        state["edge_cases"] = edge_cases
        _save_state(state)

        # Format edge cases for user
        ec_lines = []
        for i, ec in enumerate(edge_cases, 1):
            ec_lines.append(f"\n**CASE {i}: {ec['scenario']}**")
            for qi, q in enumerate(ec.get("questions", []), 1):
                ec_lines.append(f"   Q{qi}: {q}")

        return {
            "status": "round2_ready",
            "output": f"""
╔══════════════════════════════════════════════════════════╗
║  ROUND 2: EDGE CASE HUNT — Where Does This Break?       ║
║                                                          ║
║  Based on your Round 1 answers, here are the most       ║
║  likely failure points. For each:                       ║
║                                                          ║
║    ACCEPT  → Spec handles it, build includes it          ║
║    MITIGATE → Partial solution (describe briefly)       ║
║    OUT OF SCOPE → Won't be built (accept the risk)       ║
║                                                          ║
║  Answer: CASE N: ACCEPT/MITIGATE/OUT OF SCOPE           ║
╚══════════════════════════════════════════════════════════╝
{"".join(ec_lines)}
""",
            "next_action": "round2",
            "edge_cases": edge_cases,
            "round": 2,
            "ci_delta": 0,
        }

    # ── ROUND 2: Process edge case resolutions ───────────────────────────────
    elif action == "round2":
        resolutions = context.get("resolutions", {})

        state["edge_case_resolutions"] = resolutions
        state["round"] = "write"
        _save_state(state)

        task = state.get("task", task)
        discovery = {
            "content": state.get("discovery_content", ""),
            "path": state.get("discovery_path"),
        }

        # Resolve edge cases into structured dicts
        resolved = []
        edge_cases = state.get("edge_cases", [])
        for ec in edge_cases:
            ec_id = ec.get("id", "")
            resolution = resolutions.get(ec_id, resolutions.get(str(ec_cases.index(ec) + 1), "OUT OF SCOPE"))
            ec_copy = dict(ec)
            ec_copy["resolution"] = resolution
            resolved.append(ec_copy)

        state["resolved_edge_cases"] = resolved

        # Check UI library
        disc_content = state.get("discovery_content", "")
        ui_result = _check_ui_library(task, disc_content)
        if ui_result:
            state["ui_library"] = ui_result

        _save_state(state)

        # Build and write SPEC.md
        spec_content = _build_spec_content(
            task=task,
            discovery=discovery,
            round1_answers=state.get("round1_answers", {}),
            resolved_edge_cases=resolved,
            ui_library_result=ui_result,
        )

        # Write SPEC.md (atomic: temp file + fsync + rename)
        spec_path = _NEUTRON_ROOT / "SPEC.md"
        atomic_write(spec_path, spec_content)
        state["spec_written"] = True
        state["spec_path"] = str(spec_path.relative_to(_NEUTRON_ROOT))
        _save_state(state)

        # Lint
        issues = _lint_spec(spec_content)
        lint_note = ""
        if issues:
            lint_note = "\n\n⚠️  SPEC Lint (review before approving):\n"
            lint_note += "\n".join(f"   - {issue}" for issue in issues)

        return {
            "status": "spec_written",
            "spec_path": str(spec_path.relative_to(_NEUTRON_ROOT)),
            "output": (
                f"✅ SPEC.md written to: `{spec_path.relative_to(_NEUTRON_ROOT)}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔒 SPEC REVIEW — HARD GATE\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "SPEC has been hardened through 2 rounds of adversarial debate.\n"
                "Read SPEC.md above. Answer ONE of:\n\n"
                "A) **APPROVE** — \"Build it.\"\n"
                "   → workflow(step='spec', approved=True)\n\n"
                "B) **REQUEST CHANGES** — \"Change X, Y before building\"\n"
                "   → I will revise SPEC.md and present again\n\n"
                "C) **ABANDON** — \"Not what I need.\"\n"
                "   → Workflow ends. Nothing built.\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                f"{lint_note}\n"
                "SPEC.md is ready for your review above.\n"
            ),
            "next_action": "approve",
            "round": 3,
            "lint_issues": issues,
            "ui_library": ui_result,
            "ci_delta": 5,
        }

    # ── APPROVE: User approved SPEC ──────────────────────────────────────────
    elif action == "approve":
        _clear_state()

        # Also write the workflow gate so /build can run without requiring
        # the user to call workflow(step='spec', approved=True) explicitly.
        gate = _load_workflow_gate()
        gate["spec_approved"] = True
        gate["spec_approved_at"] = datetime.now().isoformat()
        gate["spec_approver_notes"] = context.get("notes", "")
        _save_workflow_gate(gate)

        return {
            "status": "spec_approved",
            "output": (
                "✅ SPEC APPROVED. BUILD IS UNLOCKED.\n\n"
                "Run: workflow(step='build')\n"
            ),
            "can_build": True,
            "ci_delta": 5,
        }

    # ── REVISE: User requested changes ───────────────────────────────────────
    elif action == "revise":
        changes = context.get("changes", "")
        state["revision_notes"] = changes
        state["round"] = "write"
        _save_state(state)

        return {
            "status": "revision_needed",
            "output": (
                f"Noted. Changes requested:\n{changes}\n\n"
                "I will revise SPEC.md and present the updated version."
            ),
            "next_action": "round3_revised",
            "revision_notes": changes,
            "ci_delta": 0,
        }

    # ── WRITE (post-revision) ─────────────────────────────────────────────────
    elif action == "write":
        task = state.get("task", task)
        discovery = {
            "content": state.get("discovery_content", ""),
            "path": state.get("discovery_path"),
        }

        resolved = state.get("resolved_edge_cases", [])
        ui_result = state.get("ui_library")

        spec_content = _build_spec_content(
            task=task,
            discovery=discovery,
            round1_answers=state.get("round1_answers", {}),
            resolved_edge_cases=resolved,
            ui_library_result=ui_result,
        )

        # Append revision note if this is a revision
        if state.get("revision_notes"):
            spec_content += (
                f"\n\n---\n"
                f"*Revision notes (from user): {state['revision_notes']}*\n"
            )

        spec_path = _NEUTRON_ROOT / "SPEC.md"
        atomic_write(spec_path, spec_content)
        state["spec_written"] = True
        state["spec_path"] = str(spec_path.relative_to(_NEUTRON_ROOT))
        _save_state(state)

        return {
            "status": "spec_written",
            "spec_path": str(spec_path.relative_to(_NEUTRON_ROOT)),
            "output": (
                f"✅ SPEC.md revised: `{spec_path.relative_to(_NEUTRON_ROOT)}`\n\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n"
                "🔒 SPEC REVIEW — HARD GATE\n"
                "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
                "Read the revised SPEC.md above.\n"
                "A) **APPROVE** — \"Build it.\"\n"
                "B) **REQUEST CHANGES** — \"Change X, Y\"\n"
                "C) **ABANDON**\n"
            ),
            "next_action": "approve",
            "round": 3,
            "ci_delta": 1,
        }

    return {"status": "error", "output": f"Unknown action: {action}", "ci_delta": 0}
