---
name: spec
type: core
version: 1.0.0
CI: 50
dependencies: [discovery, ui_library, context]
last_dream: 2026-04-14
---

## SPEC Debate Skill — Adversarial Iteration Before Build

### Purpose

**Before writing SPEC.md**, the AI conducts an adversarial debate session with the user
to challenge assumptions, surface hidden edge cases, and ensure the spec is airtight.
SPEC is not just written — it is **debated, questioned, and hardened** until both AI and user agree it's ready.

This skill runs AFTER `/discovery` and BEFORE the workflow's USER REVIEW gate.
It replaces the passive "read and approve" flow with an active adversarial loop.

---

## 🚨 CRITICAL — Auto-Confirm Enforcement (MANDATORY)

**STEP 1:** Read `memory/.auto_confirm.json`

**STEP 2:** Decision tree:
```
IF file NOT exists → run normal debate below
IF {"enabled": true} AND {"spec": true}:
    ✅ SKIP DEBATE — do NOT ask any debate questions
    ✅ Write SPEC.md directly
    ✅ Proceed to build (gate already bypassed by workflow)
    ✅ Do NOT ask "any questions?" — the spec is auto-approved

IF {"enabled": false} OR {"spec": false}:
    → Run full adversarial debate below
```

---

## How It Works

This skill runs a **3-round adversarial debate loop**:

```
Discovery output
    ↓
Round 1: ASSUMPTION CHALLENGE   ← AI challenges what was assumed
    ↓
Round 2: EDGE CASE HUNT         ← AI finds hidden failure modes
    ↓
Round 3: SPEC REFINEMENT        ← AI rewrites SPEC.md with hard requirements
    ↓
USER APPROVES (HARD GATE)       ← User says "Build it" or "Change X,Y"
```

---

## Debate Flow

### Before Starting: Load Inputs

1. Read discovery output from `memory/discoveries/{date}/{slug}/DISCOVERY.md`
2. Read existing SPEC.md if already written
3. Check `memory/LEARNED.md` for relevant past bugs → warn if similar problem exists
4. Load `skills/core/ui_library/ui_libraries.json` if frontend project

---

### Round 1: ASSUMPTION CHALLENGE

**Goal:** Surface what the user DIDN'T say but MIGHT have assumed.

Ask ALL of these (at minimum — pick the 5 most relevant to the project):

**Architecture & Scale**
1. "You mentioned [feature X]. What happens if 10,000 users try it simultaneously?"
2. "Does [component Y] need to work offline? Or is it always online?"
3. "You chose [stack]. What if that library/framework is abandoned or has a breaking change?"

**Data & State**
4. "What happens to user data if [action Z] fails halfway through? Is it rolled back?"
5. "Where does [data type] live — browser, server, both? Who owns the source of truth?"

**UX & Error Handling**
6. "What should the user see if [common failure] happens? What's the error message?"
7. "You described [UX flow]. What if the user goes BACK in the middle of it?"
8. "Is [feature] required for the app to work, or is it optional/nice-to-have?"

**Security & Access**
9. "Who can see [data/feature]? What if someone tries to access someone else's data?"
10. "You didn't mention authentication — does [feature] need login?"

**Edge Cases**
11. "What if the user uploads a [large/corrupt/invalid] file?"
12. "Does [feature] work the same on mobile as desktop?"

**Format for Round 1:**
```
╔══════════════════════════════════════════════════════════╗
║  ROUND 1: ASSUMPTION CHALLENGE                          ║
║                                                          ║
║  Before I write the spec, I need to challenge some      ║
║  assumptions. Answer what you know — say "skip" for     ║
║  what truly doesn't apply.                               ║
║                                                          ║
║  Q1: [question]                                         ║
║  Q2: [question]                                         ║
║  ...                                                     ║
║                                                          ║
║  (You can also say "I don't know yet" — better to       ║
║   surface uncertainty now than discover it in build)    ║
╚══════════════════════════════════════════════════════════╝
```

**Exit criteria:** User answered ≥ 5 questions (or explicitly said "skip the rest, I trust you").

---

### Round 2: EDGE CASE HUNT

**Goal:** Find scenarios where the system BREAKS, not where it works.

After reviewing answers from Round 1, present 3-5 specific edge cases as IF-THEN scenarios:

```
╔══════════════════════════════════════════════════════════╗
║  ROUND 2: EDGE CASE HUNT — Where Does This Break?       ║
║                                                          ║
║  I've identified the most likely failure points.         ║
║  For each, tell me: ACCEPT / MITIGATE / OUT OF SCOPE     ║
║                                                          ║
║  CASE 1: [scenario — e.g., "User loses internet mid-checkout"]║
║   → What's the expected behavior?                       ║
║                                                          ║
║  CASE 2: [scenario — e.g., "API returns 500 on first load"]║
║   → What's the expected behavior?                       ║
║                                                          ║
║  CASE 3: [scenario — e.g., "User submits form twice rapidly"]║
║   → What's the expected behavior?                       ║
╚══════════════════════════════════════════════════════════╝
```

**Rules for Round 2:**
- Generate scenarios BASED on the project's technology and discovery answers
- If project uses external API → edge case: "API is down/rate-limited"
- If project has user accounts → edge case: "user tries to access another user's data"
- If project has file upload → edge case: "file is too large / wrong format / corrupt"
- If project has payments → edge case: "payment succeeds but confirmation fails"
- If project is real-time → edge case: "connection drops mid-operation"
- If project has authentication → edge case: "session expires during action"

**Exit criteria:** User resolved ≥ 3 edge cases. Others can be marked OUT OF SCOPE.

---

### Round 3: SPEC REFINEMENT

**Goal:** Write a SPEC.md that is **specific, measurable, and unambiguous**.
No vague requirements. Every acceptance criterion has a concrete test.

**SPEC.md Structure:**

```markdown
# SPEC.md — [Project Name]

## 1. Problem Statement
[2-3 sentences. What problem does this solve? Who has it?]

## 2. Success Criteria (MEASURABLE — not "works well")
- [ ] Criterion 1: [specific metric or behavior]
- [ ] Criterion 2: [specific metric or behavior]
- [ ] ...

## 3. Tech Stack
- **Framework:** [X] — reason for choice
- **Database:** [X] — reason for choice
- **UI Library:** [X] — (if frontend: call `route_ui_library()`)
  - Install: `command`
- **Other:** [X]

## 4. Out of Scope (Explicit Exclusions)
What will NOT be built:
- ❌ [Feature A]
- ❌ [Feature B]

## 5. Functionality Specification

### Core Features
| Feature | Description | Priority |
|---------|-------------|----------|
| [F1]   | [What it does] | MUST |
| [F2]   | [What it does] | MUST |

### Data Model
| Entity | Fields | Notes |
|--------|--------|-------|
| [Entity] | [fields] | [notes] |

### API Endpoints (if applicable)
| Method | Path | Input | Output | Error |
|--------|------|-------|--------|-------|
| POST | /api/X | JSON | JSON | 400/401/500 |

### Edge Cases (resolved from Round 2)
| Scenario | Resolution |
|----------|------------|
| [EC1] | [What happens] |
| [EC2] | [What happens] |

## 6. User Acceptance Criteria (What USER verifies)
These are the checkboxes the USER runs through during acceptance test:
- [ ] [Criterion 1]
- [ ] [Criterion 2]

## 7. File Structure
```
/
├── file1
├── file2
└── ...
```

## 8. Open Questions (answered in Round 1)
| Question | Answer |
|----------|--------|
| [Q]    | [A] |
```

**Key principle:** Every item in "Success Criteria" and "User Acceptance Criteria" must be testable. NOT "works well" — instead "returns 200 within 500ms".

---

### USER APPROVAL GATE

After presenting SPEC.md (with Round 1+2 baked in):

```
╔══════════════════════════════════════════════════════════╗
║  🔒 SPEC REVIEW — HARD GATE                             ║
║                                                          ║
║  The spec above has been challenged and hardened.       ║
║  Read it. Answer ONE of:                                ║
║                                                          ║
║  A) "Build it." — APPROVE                               ║
║     → workflow(step='spec', approved=True)              ║
║                                                          ║
║  B) "Change X, Y." — REQUEST CHANGES                    ║
║     → I will revise SPEC.md and present again           ║
║     → Loop until you approve                            ║
║                                                          ║
║  C) "Abandon." — STOP                                   ║
║     → Nothing is built. Workflow ends.                  ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

---

## Integration

- **Called by:** Workflow skill (`/spec` step) — AFTER discovery is complete
- **Calls:** `skills/core/ui_library/logic/route_ui_library()` (frontend projects)
- **Loads:** `memory/discoveries/` for discovery output
- **Writes:** `SPEC.md` to project root
- **Dependency check:** discovery must be complete before this skill runs

---

## CI Update
- Full 3-round debate completed: **+5 CI**
- Edge case surfaced and resolved before build: **+3 CI**
- SPEC revised after user request-changes (per revision): **+1 CI**
- Debate skipped / assumptions made without asking: **-5 CI**
