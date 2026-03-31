---
name: workflow
type: core
version: 2.0.0
CI: 50
dependencies: [context, memory, engine, discovery, acceptance_test]
last_dream: null
---

## Execution Logic — NEUTRON EVO OS Workflow v2.0

### Purpose
Execute the structured project delivery workflow with human-in-the-loop gates.
Every non-trivial project goes through ALL 5 steps. No skipping.

---

## The 5-Step Pipeline

```
USER IDEA
    ↓
/explore     → Understand problem space, check system health
    ↓
/discovery    → Structured interview: AI asks 12 clarifying questions
    ↓
/spec        → Write SPEC.md → USER REVIEW (HARD GATE — must approve before build)
    ↓
/build       → Implement exactly what SPEC says
    ↓
/acceptance_test  → USER runs the app, verifies it solves their problem
    ↓
/ship        → Deliver, archive, update rating
    ↓
ITERATE (if acceptance failed) or DONE
```

### Key Principle: USER REVIEW Gate
> **The AI NEVER builds without the user's explicit approval of the SPEC.**
> This is the single most important gate in the entire workflow.
> Build = user has approved SPEC. No approval = no build.

---

## Step 1: /explore

**Goal**: Verify system health and understand the problem space.

**Actions**:
1. Read SOUL.md, MANIFESTO.md (identity check)
2. Audit PERFORMANCE_LEDGER.md — block if any required skill CI < 30
3. Audit memory/ — find relevant prior decisions
4. Read existing codebase (if project exists)
5. Draft a 1-paragraph problem statement

**Exit gate**: Problem statement written. System ready.

---

## Step 2: /discovery

**Goal**: Before writing SPEC, ensure the AI understands what the user actually needs.

**Actions**:
1. Call `discovery(action='start', task='<user idea>')`
2. Present 3-sentence confirmation summary to user
3. Ask 12 structured clarifying questions (12 required, 4 optional)
4. Record answers as they come in
5. When all required questions answered → generate complexity estimate + risks
6. Write output to `memory/discoveries/{date}/{slug}/DISCOVERY.md`

**Exit gate**: All 12 required questions answered. User confirmed summary. Discovery output saved.

---

## Step 3: /spec

**Goal**: Define exactly what will be built — in writing, for user approval.

**Actions**:
1. Read discovery output from `memory/discoveries/`
2. Write `SPEC.md` with:
   - Problem statement
   - Success criteria (measurable, not "works well")
   - Tech stack (AI recommends, user confirms)
   - Out of scope (explicit exclusions)
   - Acceptance criteria — what USER will verify at acceptance test
   - Edge cases
   - Files to create/modify/delete
3. Present SPEC to user for review

**HARD GATE — USER REVIEW**:
```
┌─────────────────────────────────────────────────────┐
│  SPEC REVIEW                                          │
│                                                      │
│  Read SPEC.md above. Answer ONE of:                  │
│                                                      │
│  A) APPROVE — "Build it."                            │
│     → /build is now UNLOCKED                          │
│                                                      │
│  B) REQUEST CHANGES — "Change X, Y before building"  │
│     → AI revises SPEC, presents again                │
│     → Loop until USER APPROVES                        │
│                                                      │
│  C) ABANDON — "Not what I need"                       │
│     → Workflow ends, nothing built                    │
└─────────────────────────────────────────────────────┘
```

**Exit gate**: User answered "APPROVE" or equivalent. Gate recorded in memory.

---

## Step 4: /build

**Goal**: Implement exactly what SPEC.md says — no more, no less.

**Actions**:
1. Archive before any deletion (`memory skill archive`)
2. Implement each acceptance criterion from SPEC.md
3. Anti-slop check (every output):
   - Can I defend this with evidence?
   - Is this the minimum sufficient answer?
4. Log milestone at 25%, 50%, 75%, 100%
5. Do NOT add features not in SPEC.md

**Exit gate**: All acceptance criteria implemented in code. SPEC.md itemized checklist addressed.

---

## Step 5: /acceptance_test

**Goal**: USER verifies that the build solves their actual problem.

**Actions**:
1. Call `acceptance_test(action='prepare')`
2. Generate test script based on tech stack (Python/JS/Shell)
3. Present test to user with clear run instructions
4. USER runs the app and test
5. USER decides pass or fail

**Acceptance Gate**:
```
┌──────────────────────────────────────────────────────┐
│  YOUR ACCEPTANCE TEST                                 │
│                                                       │
│  Run: [TEST COMMAND]                                  │
│  Expected: [what should happen]                       │
│                                                       │
│  If it works for you:                                 │
│    → acceptance_test(action='pass', notes='...')     │
│    → /ship is UNLOCKED                                │
│                                                       │
│  If something is wrong:                               │
│    → acceptance_test(action='fail', notes='X, Y')    │
│    → /build resumes with specific fixes                │
└──────────────────────────────────────────────────────┘
```

**Exit gate**: User confirmed acceptance (pass). `/ship` unlocked.

---

## Step 6: /ship

**Goal**: Deliver, record, rate.

**Actions**:
1. Present 3-5 bullet delivery summary to user
2. Archive SPEC.md to `memory/`
3. Update USER DECISIONS log (not skill executions)
4. Call USER RATING prompt (ask user to rate quality)
5. Delete SPEC.md from working directory

**Exit gate**: User rating recorded. Deliverable summary accepted.

---

## Step 7: /auto — Auto-Confirm Control

**Goal**: Enable or disable auto-confirm mode. Skip USER REVIEW gates when enabled.

**Usage**:
```
workflow(step='auto', mode='full')              → Enable all gates auto-confirm
workflow(step='auto', mode='spec_only')         → SPEC auto-approved only
workflow(step='auto', mode='acceptance_only')   → Acceptance auto-pass only
workflow(step='auto', mode='disable')           → Disable (all gates require user)
workflow(step='auto')                          → Toggle on/off
```

**Modes**:
| Mode | Discovery | SPEC | Acceptance |
|------|-----------|------|------------|
| `full` | SKIP | AUTO-APPROVE | AUTO-PASS |
| `spec_only` | REQUIRED | AUTO-APPROVE | REQUIRED |
| `acceptance_only` | REQUIRED | REQUIRED | AUTO-PASS |
| `spec_and_acceptance` | REQUIRED | AUTO-APPROVE | AUTO-PASS |
| `discovery_only` | SKIP | REQUIRED | REQUIRED |
| `disable` | REQUIRED | REQUIRED | REQUIRED |

**User rating at /ship is ALWAYS recorded** — even in auto mode.

---

## CI Update (v2.0 — replaced by USER RATING)
See `PERFORMANCE_LEDGER.md` for the new rating system.

Workflow CI updates only:
- Full 6-step workflow with clean acceptance: **+15 CI**
- Acceptance failed, needed rework: **-3 CI** (per iteration)
- USER REVIEW gate reached but user abandoned: **+0 CI**
- Anti-slop violation during build: **BLOCK → fix before continuing**

---

## Step Names (for AI routing)
| Step | Command | Gate |
|------|---------|------|
| Explore | `/explore` | None |
| Discovery | `/discovery` | User answers questions |
| Spec | `/spec` | **USER APPROVES SPEC** |
| Build | `/build` | SPEC approved |
| Acceptance | `/acceptance_test` | **USER RUNS + CONFIRMS** |
| Ship | `/ship` | Acceptance passed |
| Auto | `/auto` | Control auto-confirm mode |
