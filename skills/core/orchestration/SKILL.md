---
name: orchestration
type: core
version: 2.1.0
CI: 50
dependencies: [workflow, context, memory]
last_dream: null
---

## Orchestration Skill — Task Decomposition + Parallel Coordination

### Purpose

This skill decomposes large tasks into independent units and coordinates parallel execution.
It is a **PLANNING + COORDINATION tool** — it does NOT spawn agents directly.
Agents are spawned via Claude Code's built-in `/batch` command (git worktree-based parallel).

**This skill answers**: "How do I split this work? Which agents do what?
How do I make sure they don't conflict? How do I merge their outputs?"

---

---

## How to Run

```
run_orchestration(task, {"phase": "analyze"})   → Decompose task, score parallelism
run_orchestration(task, {"phase": "plan"})     → Present plan (after analyze)
run_orchestration(task, {"phase": "execute"})  → Build unit configs → use /batch to spawn
run_orchestration(task, {"phase": "update", "unit_id": "...", "result": {...}})  → Record unit result
run_orchestration(task, {"phase": "merge"})    → Validate + merge results
run_orchestration(task, {"phase": "report"})    → Final summary
```

### Execute Phase — neutron_spawn_agent

The `execute` phase returns unit configs. Call `neutron_spawn_agent` for each unit via MCP:

```
1. run_orchestration(..., phase="execute") → unit configs in output
2. For each unit: call neutron_spawn_agent(agent_id=unit_id, prompt=unit_prompt, ...)
   → agents run in parallel via claude-agent-sdk
3. Wait for results (or use background=True for non-blocking)
4. run_orchestration(..., phase="merge", results={...}) → validate + merge
```

Each spawned agent uses Claude Code's tools (Read/Edit/Bash/Glob/Grep) with its own context window.
Agents can run in the same project or different subdirectories (use `cwd` param to isolate).

```python
# After run_orchestration(..., phase="execute"):
configs = result["agent_configs"]  # list of agent configs

# Call Agent() for EACH config concurrently:
for cfg in configs:
    Agent(
        prompt=cfg["prompt"],
        agent=cfg["agent"],        # "Plan" | "Explore" | "general-purpose"
        background=cfg["background"],  # True = concurrent, False = blocking
        maxTurns=cfg["max_turns"],
        isolation=cfg["isolation"],   # project root path → git worktree isolation
        skills=cfg["skills"],         # ["spec", "context"] preloaded
    )

# When ALL agents finish, call:
run_orchestration(task, {"phase": "merge"})
```

**Background vs Foreground:**
- `background=True`: Agent runs concurrently while you continue. Long units (>20 min).
- `background=False`: Agent blocks until done. Short units, or when sequential is fine.

**Git worktree isolation**: `isolation="..."` runs the agent in a temporary worktree,
auto-cleaned if no changes. All units can safely touch the same file paths.

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

### Phase 4: Spawn neutron_spawn_agent for Each Unit

**For each unit, call `neutron_spawn_agent` via MCP:**
1. Copy the unit instruction from the `execute` phase output
2. Run multiple agents in parallel via `neutron_spawn_agent(agent_id=..., prompt=..., cwd=...)`
3. Track progress with `phase='update', unit_id='...', result={...}`
4. After all complete, call `phase='merge'`

**neutron_spawn_agent pattern:**
```
neutron_spawn_agent(
    agent_id="unit-1-backend",
    prompt="Implement auth module: JWT tokens, refresh flow, RBAC...",
    tools=["Read", "Edit", "Bash", "Glob", "Grep"],
    cwd="/path/to/project",
    timeout_seconds=600,
)
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

## How Orchestration Works with Claude Code

Orchestration is a **phase-based planning skill**. The `execute` phase outputs
unit configs that YOU spawn via `neutron_spawn_agent`:

```
1. run_orchestration(phase='analyze')  → Decompose task into units
2. run_orchestration(phase='plan')      → Review decomposition, confirm
3. run_orchestration(phase='execute')   → Get unit configs
4. neutron_spawn_agent(...) for each unit  ← parallel Claude Code agents
5. run_orchestration(phase='merge')      → Validate + merge results
```

**Real parallel execution**: `neutron_spawn_agent` uses `claude-agent-sdk` internally.
Each agent has its own context window and Claude Code tools.

---

## /batch Command Reference

Claude Code's `/batch` command spawns parallel agents using git worktrees:

```
/batch <instruction per unit>  → spawns agent in isolated worktree
```

Each worktree is an isolated git branch. No file conflicts between agents.
Worktrees are auto-cleaned when done.

**Unit config from `execute` phase** tells you what to pass to each `/batch`:
- `unit_id`: identifier for tracking
- `unit_name`: display name
- `prompt`: what to do
- `estimated_minutes`: expected duration
- `scope`: what files this unit owns

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
