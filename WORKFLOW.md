# WORKFLOW.md — NEUTRON EVO OS Task Execution

> For task *distribution & parallel processing* see below §Parallel Processing.
> For task *execution* see RULES.md §Part 2 (5-step workflow).
> Last Updated: 2026-03-31

---

## Document Scope

This file covers two related but distinct workflows:

| Concern | File | Description |
|---------|------|-------------|
| Task execution | RULES.md §Part 2 | Canonical 5-step: `/explore → /spec → /build → /verify → /ship` |
| Task distribution | This file §Parallel Processing | Splitting large tasks across sub-agents |

---

## 5-Step Workflow (Task Execution)

Full details in **RULES.md §Part 2 — Five-Step Agentic Workflow**.

Quick reference:

```
/explore  → Understand requirements, read SOUL.md + MANIFESTO.md first
           Exit: Confident scope definition, no critical unknowns

/spec     → Write SPEC.md, identify all files/components affected
           Exit: SPEC.md approved, CI impact assessed

/build    → Implement per SPEC.md; run /verify gates after each module
           Exit: All modules built, self-verified

/verify   → Run tests, lint, manual checks against SPEC.md
           Exit: Zero failures, CI score ≥ 40

/ship     → Write checkpoint, update memory, update PERFORMANCE_LEDGER.md
           Exit: Checkpoint saved, memory logged, CI +5 to +15
```

**Stop conditions:** Explicit `STOP_AND_ASK` triggers in RULES.md §Stop Conditions.
Never skip STOP triggers for speed.

---

## Parallel Processing (Task Distribution)

Use this when a task is **large enough to warrant sub-agents** (typically
> 2 hours of sequential work, or > 5 distinct components).

### When NOT to use parallel distribution
- Task is narrow (< 2 components, single domain)
- Components have tight sequential dependencies
- User asked for a quick answer or single file
- CI < 40 (Restricted) — parallel introduces too much coordination risk

### When to use parallel distribution
- > 3 independent modules can be built simultaneously
- Each module has a clean interface boundary
- All agents have access to the same context files
- CI score of routing agent ≥ 50 (Normal or Trusted)

---

### Step 1: ANALYZE

**Purpose:** Break the task into units that can execute independently.

```
□ 1.1  Read full requirements (SOUL.md, MANIFESTO.md, SPEC.md if exists)
□ 1.2  Identify modules / components / files
□ 1.3  Map dependencies — draw a simple dependency graph
□ 1.4  Label each node: PARALLEL (no deps) or SEQUENTIAL (depends on X)
□ 1.5  Group SEQUENTIAL nodes into ordered waves
□ 1.6  Estimate complexity per group (S/M/L/XL)
□ 1.7  Decide: Is parallel worth the coordination overhead?
```

**Output:** Wave plan — ordered list of agent groups.

**Example wave plan:**
```
Wave 1 (parallel):  Auth module, Product module, UI shell
Wave 2 (parallel):  Cart module (depends on Auth), Order module (depends on Cart)
Wave 3 (sequential): Integration test + deployment
```

**Exit criteria for Step 1:**
- Dependency graph drawn (even as ASCII text)
- No unknown dependencies
- Wave count ≤ 4 (otherwise break parent task further)

---

### Step 2: DISTRIBUTE

**Purpose:** Create a task envelope for each agent.

```
□ 2.1  Name each agent uniquely (e.g., Auth_Agent, Product_Agent)
□ 2.2  Write a concise prompt for each agent including:
        - SOUL.md philosophy (one sentence)
        - Specific scope: what files/components they own
        - What NOT to touch (other agents' scope)
        - Shared context: NEUTRON_ROOT, existing interfaces
        - Validation checklist (what "done" looks like)
□ 2.3  List all agents that must complete before this agent starts
□ 2.4  Define merge interface: how this agent's output meets others
□ 2.5  Set a timeout estimate (S=10min, M=30min, L=60min, XL=120min)
```

**Output:** One task envelope per agent.

**Envelope template:**
```markdown
## Agent: <Name>

**Mission:** <1-sentence description>

**Scope (own exclusively):**
- `src/auth/` — login, JWT, password reset
- `tests/auth/` — auth unit tests

**Do NOT touch:**
- `src/cart/` (Cart_Agent owns this)
- `src/order/` (Order_Agent owns this)

**Shared context:**
- NEUTRON_ROOT: $NEUTRON_ROOT
- Auth interface: `src/auth/interface.ts` (read-only)
- CI target: ≥ 70 (Trusted)

**Validation (must pass before declaring done):**
- [ ] `npm test -- --grep "auth"` passes
- [ ] No new lint errors introduced
- [ ] Integration test with Auth_Agent's JWT module passes

**Depends on:** None (Wave 1)
**Timeout estimate:** M (30 min)
```

---

### Step 3: EXECUTE

**Purpose:** Launch all Wave-1 agents in parallel, then proceed wave by wave.

```
□ 3.1  Launch all Wave-1 agents simultaneously
□ 3.2  Monitor each agent — collect their first status update
□ 3.3  If an agent fails: STOP it, assess, reassign or handle sequentially
□ 3.4  On Wave N complete: verify outputs before launching Wave N+1
□ 3.5  Track which files each agent modified
□ 3.6  Collect outputs and error logs as agents complete
```

**Output:** Per-agent result objects or error reports.

**Monitoring protocol:**
- Wave-1 agents: check in every 5 minutes
- Wave-2+ agents: check in every 10 minutes
- If no check-in after 2× timeout: STOP and reassign

---

### Step 4: VERIFY & MERGE

**Purpose:** Validate each agent's output, fix integration gaps, merge.

```
□ 4.1  Verify each agent's output against their validation checklist
□ 4.2  Check interface compatibility:
        - Do types match across agent boundaries?
        - Are shared constants consistent?
        - Are there import conflicts?
□ 4.3  Fix any integration issues found
□ 4.4  Run combined integration test
□ 4.5  Run linter and type checker on merged codebase
□ 4.6  Verify SPEC.md requirements still met (may need update)
□ 4.7  Merge outputs into a coherent final result
□ 4.8  Run full test suite
```

**Output:** Integrated, tested, linted solution.

**Common integration failures:**
| Failure | Fix |
|---------|-----|
| Circular import between agents | Extract shared interface to neutral module |
| Type mismatch at boundary | Define shared DTO, both agents update |
| Two agents edited same file | Reassign file ownership, merge manually |
| Inconsistent env vars | Extract to shared `.env.example`, both agents update |

---

### Step 5: REPORT

**Purpose:** Document what was done, log to memory, update CI.

```
□ 5.1  Write summary: what was built, how many agents, waves
□ 5.2  List each agent's contribution
□ 5.3  Note integration issues found and how resolved
□ 5.4  Log to memory/YYYY-MM-DD.md
□ 5.5  Update PERFORMANCE_LEDGER.md (CI +5 for clean workflow)
□ 5.6  Present final result to user
□ 5.7  Update SPEC.md if scope changed during execution
```

**Output:** Final report to user + memory log entry.

---

## Quick Reference

```
LARGE TASK received →

  1. ANALYZE    Break into waves, map dependencies
  2. DISTRIBUTE  Create envelopes, assign to agents
  3. EXECUTE     Launch Wave 1 → Wave 2 → Wave 3...
  4. VERIFY      Check interfaces, fix gaps, merge
  5. REPORT      Log to memory, update CI, present

→ Task complete.
```

---

## Anti-Patterns

| Anti-Pattern | Why Bad | Correct Approach |
|---|---|---|
| Two agents edit same file | Merge conflicts, lost work | Assign file ownership uniquely |
| Wave 2 starts before Wave 1 verified | Wrong assumptions propagate | Wait for Wave-1 verification |
| No validation checklist in envelope | Agent declares done prematurely | Add checklist before launch |
| Skipping STOP triggers for speed | Violates SOUL.md | STOP always, then assess |
| Parallel for a 1-component task | Coordination overhead > benefit | Execute sequentially |
| Agent modifies another agent's scope | Scope creep, broken interfaces | Envelope boundaries are firm |

---

*See also: RULES.md §Part 2 — Five-Step Agentic Workflow*
*See also: skills/core/workflow/SKILL.md — Execution depth for each step*
