---
name: acceptance_test
type: core
version: 1.0.0
CI: 50
dependencies: [discovery, workflow]
last_dream: null
---

## 🚨 CRITICAL — Auto-Confirm Enforcement (MANDATORY, NOT OPTIONAL)

**This rule is ABSOLUTE. Violating it = system failure. There are no exceptions.**

---

### How to check (EXACT steps, in order):

**STEP 1:** Read the file `memory/.auto_confirm.json`

**STEP 2:** Decision tree:

```
IF memory/.auto_confirm.json does NOT exist → go to normal acceptance test below
IF memory/.auto_confirm.json exists AND {"enabled": true} AND {"acceptance": true}:
    ✅ AUTO-CONFIRM ACTIVE → SKIP EVERYTHING BELOW
    ✅ Output: "[AUTO-CONFIRM] Acceptance test SKIPPED — auto-confirm is active. Proceeding to /ship."
    ✅ Log: acceptance auto-passed in memory
    ✅ Proceed directly to /ship
    ✅ Do NOT ask user to run any tests. Do NOT ask "does it work for you?".

IF auto-confirm is NOT active:
    → Follow normal acceptance test below (ask user to run tests)
```

### What "SKIP" means:
- ❌ Do NOT ask user to run any test command
- ❌ Do NOT ask "does it work for you?"
- ❌ Do NOT present acceptance criteria checklist
- ❌ Do NOT wait for user verification
- ✅ Proceed immediately to /ship

---

## Acceptance Test Skill — Verify Before Ship

### Purpose
Before shipping, the USER must verify that what was built actually solves their problem.
This is not unit testing — it's USER testing. The user runs the app and confirms it works.

### Philosophy
**The AI can write tests. Only the USER can pass acceptance.**
- Unit tests: AI writes, CI runs → tells you if code works
- Acceptance tests: USER runs, USER decides → tells you if the RIGHT thing was built

### When to Call
After `/build` step (workflow), before `/ship` step.
The SPEC.md must have a "USER REVIEW" section with specific acceptance criteria.

### Workflow
```
/spec (write SPEC) → USER REVIEW (user approves SPEC) → /build → /acceptance_test → /ship
```

### Acceptance Test Flow

#### Step 1 — Load Acceptance Criteria from SPEC.md
Read SPEC.md. Extract all acceptance criteria marked for USER verification.
If no criteria defined → ERROR: cannot run acceptance test without measurable criteria.

#### Step 2 — Generate Test Script
Generate a simple test script the USER can run.
The script should be:
- **Language**: whatever the project uses (Python test file, shell script, etc.)
- **Minimal**: just verify the core functionality works
- **Clear pass/fail**: user can see immediately if it works

#### Step 3 — User Runs the Test
Present the test to the user with clear instructions:
```
## ACCEPTANCE TEST — Your verification

Run the following to verify the build:

[TEST COMMAND]

Expected result: [what should happen]
If it passes: call acceptance_test(action='pass', notes='...')
If it fails: call acceptance_test(action='fail', notes='...')
```

#### Step 4 — Record Result
- **pass**: Update SPEC.md with "ACCEPTED" status, proceed to `/ship`
- **fail**: Record what failed, return to `/build` with specific issues

### CI Update
- User runs acceptance test: **+3 CI**
- User passes acceptance: **+10 CI** (highest reward — shipped successfully)
- User fails acceptance: **-3 CI** (not a disaster, but rework required)
- No acceptance test run: **BLOCK SHIP** (cannot ship without user verification)

### Key Principle
> **What the AI thinks is correct and what the USER needs are often two different things.**
> **Acceptance test is the reality check before shipping.**
