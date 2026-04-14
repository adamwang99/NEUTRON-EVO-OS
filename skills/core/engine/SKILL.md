---
name: engine
type: core
version: 1.0.0
CI: 50
dependencies: []
last_dream: 2026-04-14
---

## Execution Logic

### Purpose
The Expert Skill Router — NEUTRON EVO OS's central dispatch engine. Audits PERFORMANCE_LEDGER.md before executing any skill. Routes tasks to appropriate skills based on CI scores and availability.

---

## Routing Protocol

### Pre-Route Audit
Before any task dispatch:
1. Read `PERFORMANCE_LEDGER.md`
2. For each candidate skill, retrieve CI score
3. Check dependencies are satisfied
4. **BLOCK** if any required skill has CI < 30

### CI-Gated Routing Table
| CI Score | Routing Behavior |
|----------|-----------------|
| >= 70 | Full trust — auto-route, auto-execute |
| 40-69 | Route with verbose logging |
| 30-39 | Route with explicit verification gate |
| < 30 | **BLOCK** — require human review before dispatch |

### Skill Priority
When multiple skills match a task:
1. Prefer highest CI score
2. Break ties by task count (more experienced → higher priority)
3. Check dependencies are satisfied

### Available Skills
| Skill | Path | Type | Dependencies |
|-------|------|------|-------------|
| context | `skills/core/context/SKILL.md` | core | none |
| memory | `skills/core/memory/SKILL.md` | core | none |
| workflow | `skills/core/workflow/SKILL.md` | core | context, memory |
| engine | `skills/core/engine/SKILL.md` | core | none |

---

## Engine Components

### expert_skill_router.py
- `get_ledger_entry(skill_name)`: Read CI from PERFORMANCE_LEDGER.md
- `route_task(task, context)`: Return {skill, confidence, reasoning}
- `execute_skill(skill_path, task)`: Execute after CI audit passes
- `audit()`: Full system CI health check

### smart_observer.py
- Watches source file changes via watchdog
- 30-second debounce: only fires Dream Cycle after work settles
- Non-blocking: runs in background thread
- `start_observer(root_path, callback, debounce_seconds=30)`

### dream_engine.py
- `dream_cycle()`: Full Memory 2.0 cycle (archive + prune + distill)
- `distill_log(log_path)`: Compress log into Cookbook summary
- `NOISE_THRESHOLD = 3` days (files older without reference)
- Archives to `/memory/archived/`
- Cookbooks go to `/memory/cookbooks/`

---

## Smart Observer Behavior
- Trigger: File modified in watched directory
- Debounce: 30 seconds of no new changes before firing
- Purpose: Wait for work to "settle" before triggering expensive Dream Cycle
- Coalescing: Multiple rapid changes fire ONE Dream Cycle after last change

---

## CI Update
After engine skill execution:
- Routing completed without errors: **+2 CI**
- Dream Cycle triggered and completed: **+10 CI**
- BLOCK triggered (CI < 30 detected): **+5 CI** (safety contribution)
- False positive BLOCK (skill was actually fine): **-3 CI**
