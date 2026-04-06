# NEUTRON EVO OS — Audit Notes 2026-04-06

## Version

**Current:** V4 post-upgrade-v2 (`16d6150`) + hotfix (`d0c3c3f`)
**CI:** 78/78 tests passing

---

## System State (Post Upgrade V2)

### Token Overhead: ~6,776 tokens (down from ~8,000)

| File | Tokens |
|------|--------|
| SOUL.md | ~1,657 |
| RULES.md | ~2,546 |
| GOVERNANCE.md | ~1,686 |
| NEUTRON_CONTEXT.md | ~478 |
| CLAUDE.md | ~410 |
| session-start.sh (echo) | ~400-1K |

### CI State (Live — Regex Fixed)

| Skill | CI | Status |
|-------|-----|--------|
| workflow | 55 | normal → trusted |
| spec | 47 | normal |
| context | 50 | normal |
| memory | 50 | normal |
| engine | 50 | normal |
| discovery | 50 | normal |
| acceptance_test | 50 | normal |
| orchestration | 50 | normal |
| checkpoint | 50 | normal |
| learned | 35 | normal |

### CI Thresholds

- 70-100: **Trusted** (auto-confirm enabled)
- 40-69: **Normal** (standard operation)
- 20-29: **Restricted** (warning, still runs)
- 0-19: **Rehabilitation** (confidence ×0.7, still runs)

### CI Delta Rules (Active)

| Rating | Delta |
|--------|-------|
| 5 | +5 CI |
| 4 | +3 CI |
| 3 | 0 (neutral) |
| 2 | -3 CI |
| 1 | -5 CI |

### Memory System

- SHORT: `memory/YYYY-MM-DD.md` — session logs, 500-line cap → Dream archive
- MID: `memory/cookbooks/` — 5 files, Dream Cycle auto every 12h
- LONG: `memory/LEARNED.md` — 7 bug entries, echoed at session start + build-time recall

### Swarm Agent

- `neutron_spawn_agent` MCP tool — `claude-agent-sdk` with `asyncio.run()` fix
- `spawn_parallel(unit_configs)` — true N-agent parallel via `ThreadPoolExecutor(max_workers=N)`

---

## Remaining Issues (Priority Order)

### P1: Routing Keyword Gaps

**"fix filelock timeout bug"** → falls through to default (confidence=0.3, workflow).
Root cause: keyword map missing `bug`, `fix`, `crash`, `error`, `debug`, `patch`.

**"build authentication module"** → falls through (keyword `build` not in workflow map).
**"orchestrate multi-agent pipeline"** → fails to route to orchestration.

### P2: Dream Cycle Never Triggered Today

`last_dream` was `null` — Dream Cycle was manual-only before today.
Session-start trigger added in upgrade-v2 (`16d6150`) — will fire next session.
**Action needed:** trigger Dream Cycle manually to seed first cookbook and close the loop.

### P3: LEARNED.md Recall Is Passive

Session-start.sh echoes LEARNED.md to terminal. Model must remember and apply.
No structured injection into context. No proactive re-check on error detection.

### P3: SOUL+RULES+GOVERNANCE Can Be Consolidated

Three files totalling ~5,900 tokens. Can be consolidated to ~2,000 tokens.
Not urgent — token savings modest.

---

## Scores (Self-Audit)

| Criteria | Before | After | Notes |
|----------|--------|-------|-------|
| Speed | 2/10 | 4/10 | SPEC enforcement + LEARNED recall |
| Token savings | 4/10 | 5/10 | -15% overhead |
| Swarm agents | 1/10 | 4/10 | Parallel spawn working |
| RULE process | 6/10 | 7/10 | Positive CI + recovery |
| 3-tier memory | 2/10 | 4/10 | Dream auto + distill→pending |
| Self-evolution | 1/10 | 3/10 | Feedback loop closed |
| **Average** | **2.7** | **4.5** | **+67%** |

---

## Commit History (This Session)

| Commit | Description |
|--------|-------------|
| `16d6150` | feat(upgrade-v2): Phase 1-7 comprehensive system upgrade |
| `d0c3c3f` | fix(ci): PERFORMANCE_LEDGER regex — 3-column format alignment |

## Next Actions

1. [ ] Fix P1: Add bug/fix/error keywords to routing map
2. [ ] Trigger Dream Cycle manually (first run)
3. [ ] Add `build` keyword to workflow routing
4. [ ] Add `orchestrat*` keyword to orchestration routing
5. [ ] (P3) Structured LEARNED injection into context
6. [ ] (P3) Consolidate SOUL+RULES+GOVERNANCE
