# NEUTRON EVO OS — Context (Keep Short)

## MANDATORY: Read this FIRST

Read `$NEUTRON_ROOT/memory/.auto_confirm.json` before doing anything.

**If `enabled: true`:**
- `discovery=true` → skip interview, write DISCOVERY.md directly, go to /spec
- `spec=true` → after SPEC.md, auto-approve, go to /build
- `acceptance=true` → after /build, auto-pass, go to /ship
- `/ship rating` is ALWAYS requested from user — never skip this

## Recall: LEARNED.md

Before writing code in `/build`, `memory/LEARNED.md` is checked for relevant past bugs.
Recent entries shown at session start. Apply them before coding.

## Workflow Steps

`/explore` → `/discovery` (12 questions) → `/spec` (3-round debate) → `/build` → `/verify` (pytest) → `/acceptance` → `/ship`

## Skills (11 core)

| Skill | Trigger keywords |
|-------|-----------------|
| context | context, compact, CLAUDE.md, ide window, token overhead |
| memory | memory, archive, search, recall, cookbook, distill, shipment |
| workflow | workflow, implement, spec, specification, user story, acceptance criteria |
| engine | engine, router, CI, audit, observer, health, status, stats |
| checkpoint | checkpoint, handoff, resume, save progress, interrupt |
| discovery | discovery, interview, requirements, clarify, ask questions |
| acceptance_test | acceptance, test, verify, pytest, coverage, unit test |
| spec | spec, debate, adversarial |
| orchestration | orchestrate, parallel, multi-agent, swarm, concurrent, worktree |
| feature_library | auth, JWT, REST, database, API |
| ui_library | UI, frontend, shadcn, Ant Design |

**Catch-all:** bug, fix, error, crash, debug, refactor → routes to workflow

## Quick Commands

```bash
neutron status          # system status + CI scores
neutron dream           # run Dream Cycle (archive + distill)
neutron memory search <keyword>   # search LEARNED.md
neutron auto full       # skip all gates
neutron gc              # garbage collection
```

## CI Scoring (Live — PERFORMANCE_LEDGER.md)

| CI Range | Status | Behavior |
|----------|--------|---------|
| 70-100 | Trusted | Auto-confirm enabled |
| 40-69 | Normal | Standard operation |
| 20-29 | Restricted | Warning, still runs |
| 0-19 | Rehabilitation | Confidence ×0.7, still runs |

**Rating → CI:** 5→+5 | 4→+3 | 3→0 | 2→-3 | 1→-5
