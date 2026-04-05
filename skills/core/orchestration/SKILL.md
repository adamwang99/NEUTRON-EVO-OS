---
name: orchestration
type: core
version: 1.0.0
CI: 50
dependencies: [workflow, context, memory]
last_dream: null
---

## Orchestration Skill — Multi-Agent Parallel Task Distribution

### Purpose

When a task is large enough to benefit from parallel execution, this skill orchestrates
multiple specialized agents working simultaneously — each agent handles a distinct unit
of work, results are aggregated and validated, and the final deliverable is assembled.

**This skill answers**: "How do I split this work? Which agents do what?
How do I make sure they don't conflict? How do I merge their outputs?"

---

## 🚨 CRITICAL — Auto-Confirm Enforcement

**STEP 1:** Read `memory/.auto_confirm.json`

**Decision tree:**
```
IF file NOT exists → run normal orchestration
IF {"enabled": true} AND {"orchestration": true}:
    ✅ Run orchestration without asking — spawn agents after presenting plan
IF {"enabled": false}:
    → Show plan → ask for confirmation → spawn
```

---

## When to Use Orchestration

**Trigger this skill when ANY of these conditions are met:**
- Task has ≥3 independent modules/components
- Task spans frontend + backend + infrastructure
- Task requires independent API integration work
- Task has multiple data models that don't depend on each other
- `/batch` would be used in a regular Claude Code session

**Do NOT use orchestration when:**
- Task is simple (< 1 hour of work)
- Task has strict sequential dependencies (each step depends on previous)
- Only one person/agent can make decisions (requires single-threaded thinking)

---

## Orchestration Protocol

### Phase 1: Task Decomposition

**Analyze the task and decompose it into ATOMIC, INDEPENDENT units.**

Rules for decomposition:
1. **No shared mutable state** — each unit must be self-contained
2. **No circular dependencies** — unit A should not depend on unit B if B depends on A
3. **Clear interfaces** — define what each unit's output looks like BEFORE spawning agents
4. **Max 8 parallel agents** — more creates coordination overhead, not speed

**Unit definition template:**
```
UNIT-[N]: [Unit Name]
  Scope: [What this agent owns]
  Files: [Files to create/modify]
  Deliverables: [What this agent must produce]
  Dependencies: [What it needs from other units]
  Interface: [How this unit's output connects to others]
```

### Phase 2: Agent Role Assignment

**Assign each unit to the right agent type:**

| Unit Type | Agent | Tools |
|-----------|-------|-------|
| Research / Architecture | Explore | Read, Grep, Glob — read-only |
| Backend / API / Logic | Plan | Read, Grep, Glob, Write, Edit, Bash |
| Frontend / UI | Plan | Read, Grep, Glob, Write, Edit, Bash |
| Testing / Verification | Plan + Test skill | Full access |
| Infrastructure / DevOps | Plan | Read, Write, Bash, Edit |
| Integration / Merge | Plan (main) | Read, Write, Edit, Bash |

**Critical rule:** Main agent = Coordinator. Workers = specialized, self-contained.

### Phase 3: Execution Plan Presentation

Present a structured plan to the user:

```
╔══════════════════════════════════════════════════════════╗
║  ORCHESTRATION PLAN — [N] PARALLEL AGENTS              ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  UNIT-1: [Name]                                         ║
║    Agent: [Type] | Scope: [X]                           ║
║    Deliverables: [Y]                                    ║
║    Est: [~N min]                                        ║
║                                                          ║
║  UNIT-2: [Name]                                         ║
║    Agent: [Type] | Scope: [X]                           ║
║    Deliverables: [Y]                                    ║
║    Est: [~N min]                                        ║
║                                                          ║
║  ...                                                     ║
║                                                          ║
║  MERGE: After all complete → [main agent] validates      ║
║          and merges outputs                             ║
║                                                          ║
║  Est. total time: [parallel time] vs [sequential time]  ║
║  Speed gain: [Nx faster]                                ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝

Proceed? (YES / Modify plan / CANCEL)
```

### Phase 4: Spawn Agents in Parallel

**For each unit, spawn an agent with:**
1. Clear scope description
2. Required context (relevant files, existing code)
3. Output format specification
4. Error handling instructions
5. What to do when done

**Spawn command pattern:**
```
Agent[unit-N]:
  Type: [Explore | Plan | general-purpose]
  Context: [Required context files]
  Task: [Specific task]
  Output: [What to produce]
  On error: [What to do]
```

### Phase 5: Progress Tracking

```
ORCHESTRATION PROGRESS:
┌──────────────────────────────────────────────────────────┐
│ Task: [Task Name]                         [Start: HH:MM] │
├──────────────────────┬─────────┬─────────┬───────────────┤
│ Agent                │ Status  │ Done    │ Output        │
├──────────────────────┼─────────┼─────────┼───────────────┤
│ UNIT-1: [Name]      │ ✅ Done │ 100%   │ [files]       │
│ UNIT-2: [Name]      │ 🔄 Run  │ 65%    │ —             │
│ UNIT-3: [Name]      │ ⏳ Wait │ 0%     │ —             │
├──────────────────────┴─────────┴─────────┴───────────────┤
│ MERGE: ⏳ Waiting for UNIT-2, UNIT-3                    │
└──────────────────────────────────────────────────────────┘
```

**Update progress after each unit completes.**

### Phase 6: Result Validation & Merge

When all agents complete:

1. **Validate each output:**
   - Did the agent produce what was promised?
   - Are there merge conflicts?
   - Are there incompatible interfaces between units?

2. **Resolve conflicts:**
   - File conflicts: main agent decides which version wins
   - Interface mismatches: main agent bridges the gap
   - Missing deliverables: request agent to redo or skip

3. **Merge:**
   - Run integration tests (if applicable)
   - Verify end-to-end flow
   - Update SPEC.md if architecture changed

### Phase 7: Report

Present unified results:

```
╔══════════════════════════════════════════════════════════╗
║  ORCHESTRATION COMPLETE                                 ║
╠══════════════════════════════════════════════════════════╣
║                                                          ║
║  ✅ UNIT-1: [Name] → [files produced]                   ║
║  ✅ UNIT-2: [Name] → [files produced]                   ║
║  ✅ UNIT-3: [Name] → [files produced]                   ║
║                                                          ║
║  Merge results: [summary]                                ║
║  Integration: [passed/failed]                            ║
║  Time saved: [Nx] vs sequential                         ║
║                                                          ║
╚══════════════════════════════════════════════════════════╝
```

---

## Integration with Claude Code Bundled Skills

**Use `/batch` for file-modification tasks:**
- `/batch migrate src/ from X to Y` — parallel file changes with git worktree
- `/batch refactor components/` — parallel refactoring across components
- This skill handles the DECISION-MAKING layer; `/batch` handles execution

**Orchestration runs BEFORE `/batch`:**
```
1. orchestration → decompose task, define units, plan merge
2. /batch → spawn parallel agents per unit (if file modification)
3. orchestration → validate, merge, report
```

---

## Conflict Prevention

**Rules to prevent agent conflicts:**

1. **File ownership:** Each file belongs to exactly ONE unit. No shared files unless explicitly defined.
2. **Interface contracts:** Before spawning, define the JSON/data structure that connects units.
3. **Sequential merge:** The main agent does ALL merging. Workers never touch each other's outputs.
4. **No mutable globals:** Infrastructure/config files = main agent only.

**If conflict detected:**
```
⚠️  CONFLICT: UNIT-[X] modified [file Y] which is owned by UNIT-[Z]
Resolution:
  1. Identify which unit modified it last
  2. UNIT-[Z] owner reviews the change
  3. Merge into both outputs or let owner take precedence
```

---

## CI Update
- Orchestration planned and executed: **+5 CI**
- Task successfully decomposed into ≥3 independent units: **+3 CI**
- All units completed with no merge conflicts: **+5 CI**
- Merge conflicts resolved without rework: **+2 CI**
- Orchestration attempted but sequential was faster (wrong trigger): **-3 CI**
