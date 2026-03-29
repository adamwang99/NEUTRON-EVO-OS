---
name: workflow
type: core
version: 1.0.0
CI: 50
dependencies: [context, memory, engine]
last_dream: null
---

## Execution Logic

### Purpose
Execute the NEUTRON EVO OS 5-step workflow: `/explore` → `/spec` → `/build` → `/verify` → `/ship`

### Workflow Gates
Each step is a gate — the next step does not begin until the current step is verified complete.

---

## Step 1: /explore

**Goal**: Understand the problem space fully before writing a line of code.

**Actions**:
1. Read SOUL.md, MANIFESTO.md, USER.md (identity check)
2. Audit PERFORMANCE_LEDGER.md for relevant skill CI scores
3. Call `engine/expert_skill_router.route_task()` to identify required skills
4. If any required skill has CI < 30: **BLOCK** — request human review
5. Research: read existing code, docs, prior logs
6. Identify constraints, dependencies, and blockers
7. Draft a problem statement

**Exit gate**: Problem statement is written and human-approved (or CI >= 70 for auto-approve).

---

## Step 2: /spec

**Goal**: Define exactly what will be built before any implementation begins.

**Actions**:
1. Write formal specification in `/spec/YYYY-MM-DD_<task-name>.md`
2. Define measurable acceptance criteria (e.g., "returns X when given Y", not "works well")
3. List constraints: performance, security, compatibility
4. Identify edge cases and define expected behavior for each
5. Get human approval if > 10 file changes or new external dependencies

**Spec template**:
```markdown
## Problem
[1-2 sentence problem statement]

## Solution
[High-level approach]

## Acceptance Criteria
- [ ] Criterion 1 (measurable)
- [ ] Criterion 2 (measurable)

## Edge Cases
- Case A: expected behavior

## Constraints
- [List any limitations]

## Files Affected
- [List files to create/modify/delete]
```

**Exit gate**: Spec is written, acceptance criteria are measurable, human-approved.

---

## Step 3: /build

**Goal**: Implement exactly what the spec says — no more, no less.

**Actions**:
1. Archive before any deletion (move to `/memory/archived/`)
2. Implement each acceptance criterion from /spec
3. Log progress to `memory/YYYY-MM-DD.md` at each milestone
4. Call expert_skill_router for sub-skill dispatch
5. Never generate Model Slop — output must be verifiable
6. Commit at logical checkpoints

**Anti-Slop Check** (every output):
- Can I defend this with evidence?
- Is this the minimum sufficient answer?
- Does this add functional value beyond the spec?

**Exit gate**: All acceptance criteria in /spec are addressed in code.

---

## Step 4: /verify

**Goal**: Confirm the implementation matches the spec exactly.

**Actions**:
1. Run unit tests: `pytest` or equivalent
2. Run integration tests
3. Manually verify each acceptance criterion
4. Check for Model Slop in output (is it repetitive, hallucinated, hollow?)
5. Audit: does this earn CI or just consume tokens?
6. If verification fails: return to /spec for clarification

**Verification checklist**:
- [ ] All acceptance criteria pass
- [ ] No regression in existing features
- [ ] No hallucinated facts or fake citations
- [ ] CI audit passed (output is verifiable and functionally valuable)
- [ ] Error handling is appropriate

**Exit gate**: All checks pass. Output earns CI.

---

## Step 5: /ship

**Goal**: Deliver, record, and maintain.

**Actions**:
1. Update PERFORMANCE_LEDGER.md: +5 CI per skill used for verified tasks
2. Log to `memory/YYYY-MM-DD.md`: task, outcome, CI delta
3. If Dream Cycle triggered (source files settled after debounce): call `dream_engine.dream_cycle()`
4. Summarize deliverables for user: 3-5 bullet points max
5. Flag any known limitations or next steps

**Exit gate**: Deliverable summary delivered, ledger updated, log written.

---

## CI Update
After full workflow completion (all 5 steps):
- All steps passed cleanly: **+15 CI** (workflow skill)
- Model Slop detected mid-workflow: **-10 CI**, return to /build
- Verification failure requiring rework: **-5 CI**
- Hallucination detected: **Immediate STOP + escalate**
