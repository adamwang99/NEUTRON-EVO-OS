"""
NEUTRON EVO OS — MCP Prompts
NEUTRON workflow step templates as MCP prompts.
NEW PIPELINE v2.0: explore → discovery → spec (USER REVIEW) → build → acceptance (USER CONFIRMS) → ship
"""
from __future__ import annotations


def list_prompts():
    return [
        {
            "name": "neutron_explore",
            "description": "Step 1: Verify system health, understand problem space",
        },
        {
            "name": "neutron_discovery",
            "description": "Step 2: Run discovery interview — ask user 12 clarifying questions BEFORE building",
        },
        {
            "name": "neutron_spec",
            "description": "Step 3: Write SPEC.md — USER REVIEW gate: must approve before build",
        },
        {
            "name": "neutron_build",
            "description": "Step 4: Implement exactly what SPEC.md says — no more, no less",
        },
        {
            "name": "neutron_acceptance",
            "description": "Step 5: USER runs the app, confirms it solves their problem",
        },
        {
            "name": "neutron_ship",
            "description": "Step 6: Deliver, archive SPEC, record user rating",
        },
    ]


def get_prompt(name: str, arguments: dict = None) -> dict:
    """Return the prompt for the given name."""
    arguments = arguments or {}
    task = arguments.get("task", "Untitled task")

    prompts_map = {
        "neutron_explore": (
            f"Run /explore for: {task}\n\n"
            "1. Read SOUL.md and MANIFESTO.md (identity check)\n"
            "2. Audit PERFORMANCE_LEDGER.md — block if any skill CI < 30\n"
            "3. Search memory/ for relevant prior decisions (USER DECISIONS LOG)\n"
            "4. Draft 1-paragraph problem statement\n"
            "5. If new project: offer to run /discovery next"
        ),
        "neutron_discovery": (
            f"Run /discovery for: {task}\n\n"
            "IMPORTANT: Never build without understanding what the user actually needs.\n\n"
            "1. Call: discovery(action='start', task='{task}')\n"
            "2. Present 3-sentence summary for user confirmation\n"
            "3. Ask ALL 12 required interview questions — do NOT skip any\n"
            "4. Record answers as they come in\n"
            "5. When all required questions answered → complexity estimate + risks\n"
            "6. Write discovery output to memory/discoveries/{date}/{slug}/DISCOVERY.md\n\n"
            "CRITICAL: If user just gave a brief idea, START THE INTERVIEW instead of assuming."
        ),
        "neutron_spec": (
            f"Write SPEC.md for: {task}\n\n"
            "1. Read discovery output from memory/discoveries/\n"
            "2. Write SPEC.md with:\n"
            "   - Problem statement (from discovery)\n"
            "   - Success criteria (measurable, not 'works well')\n"
            "   - Tech stack (AI recommends, user confirms)\n"
            "   - Out of scope (explicit exclusions)\n"
            "   - Acceptance criteria (what USER will verify at acceptance test)\n"
            "   - Edge cases and constraints\n"
            "3. Present to user with:\n\n"
            "   A) APPROVE — 'Build it.' → /build UNLOCKED\n"
            "   B) REQUEST CHANGES — → I revise, you approve again\n"
            "   C) ABANDON — → Nothing built\n\n"
            "HARD GATE: /build does not start until user APPROVES."
        ),
        "neutron_build": (
            f"Implement: {task}\n\n"
            "1. Read SPEC.md (ONLY build what is in SPEC.md)\n"
            "2. Archive before any deletion: memory(action='archive')\n"
            "3. Implement each acceptance criterion from SPEC.md\n"
            "4. Anti-slop check on every output:\n"
            "   - Can I defend this with evidence?\n"
            "   - Is this the minimum sufficient answer?\n"
            "5. Log milestone at 25%, 50%, 75%, 100%\n"
            "6. Do NOT add features not in SPEC.md\n"
            "7. After build: /acceptance_test — USER must verify"
        ),
        "neutron_acceptance": (
            f"Run acceptance test for: {task}\n\n"
            "1. Call: acceptance_test(action='prepare')\n"
            "2. Generate test script based on tech stack\n"
            "3. Present test to user with clear run instructions:\n\n"
            "   Run: [TEST COMMAND]\n"
            "   Expected: [what should happen]\n\n"
            "4. USER decides:\n"
            "   - PASS → acceptance_test(action='pass') → /ship UNLOCKED\n"
            "   - FAIL → acceptance_test(action='fail', notes='...') → return to /build\n\n"
            "CRITICAL: Only USER can pass acceptance. Not unit tests. Not AI confidence."
        ),
        "neutron_ship": (
            f"Deliver: {task}\n\n"
            "1. Archive SPEC.md to memory/ (with timestamp)\n"
            "2. Record USER DECISION: delivery completed\n"
            "3. Present 3-5 bullet delivery summary\n"
            "4. Ask user to rate: 1-5\n\n"
            "   5 = Excellent — better than expected\n"
            "   4 = Good — does what I need\n"
            "   3 = Acceptable — worked but needed fixes\n"
            "   2 = Poor — major issues\n"
            "   1 = Broken — not what I asked for\n"
            "5. Record rating: rating.add_rating(shipment_id, rating, notes)\n"
            "6. Flag next steps or known limitations"
        ),
    }

    text = prompts_map.get(name, f"Unknown prompt: {name}")
    return {"messages": [{"role": "user", "content": {"type": "text", "text": text}}]}
