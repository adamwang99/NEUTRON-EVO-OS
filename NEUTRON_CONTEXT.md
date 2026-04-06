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
| context | context, compact, CLAUDE.md, ide window |
| memory | memory, log, archive, search, recall, cookbook |
| workflow | workflow, /explore, /spec, /build, /ship, 5-step |
| engine | engine, router, CI, audit, observer, health |
| checkpoint | checkpoint, handoff, resume |
| discovery | discovery, interview, requirements |
| acceptance_test | acceptance, test, verify, user test |
| spec | spec, debate, adversarial |
| orchestration | orchestrate, parallel, multi-agent |
| feature_library | auth, JWT, REST, database, API |
| ui_library | UI, frontend, shadcn, Ant Design |

## Quick Commands

```bash
neutron status          # system status + CI scores
neutron dream           # run Dream Cycle (archive + distill)
neutron memory search <keyword>   # search LEARNED.md
neutron auto full       # skip all gates
neutron gc              # garbage collection
```

## CI Scoring

- CI ≥ 70: full trust (auto-route)
- CI ≥ 40: normal
- CI < 30: blocked (human review required)

**Low rating (1-2) at `/ship` penalizes the skills used → CI drops.**
