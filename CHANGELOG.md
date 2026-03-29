# Changelog — NEUTRON EVO OS

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [4.0.0] — 2026-03-30

### Breaking Changes

- **Global rename**: `ai-context-master` → `NEUTRON-EVO-OS`
- **Global rename**: `AI Context Master` → `NEUTRON EVO OS`
- **Global rename**: `ai-context-master` (npm package) → `neutron-evo-os`
- VS Code extension renamed: `ai-context-master` → `neutron-evo-os`, publisher updated
- Context loading order updated: MANIFESTO.md and PERFORMANCE_LEDGER.md added as mandatory layers

### New Features

- **MANIFESTO.md** — Formal ∫f(t)dt philosophy: "Functional Credibility Over Institutional Inertia"
- **Folder-based skill architecture** — Anthropic-style under `/skills/core/<name>/SKILL.md`
- **4 Core Skills**: `context`, `memory`, `workflow`, `engine` — each with `logic/` and `validation/` subpackages
- **`engine/expert_skill_router.py`** — CI-gated task routing with `audit()`, `route_task()`, `execute_skill()`, `update_ci()`
- **`engine/smart_observer.py`** — Watchdog-based file observer with 30s debounce; `SilentObserver` class for background threads
- **`engine/dream_engine.py`** — Memory 2.0: Archive + Prune (noise removal) + Distill (Cookbook compression)
- **PERFORMANCE_LEDGER.md** — Structured CI tracking per skill with CI-gated routing table
- **Evolution Dashboard** — Rich terminal UI (`evolution_dashboard.py`) with real-time CI display
- **Memory 2.0** — `/memory/archived/` (NEVER DELETE user data) + `/memory/cookbooks/` (distilled summaries)
- **5-Step Workflow** — `/explore` → `/spec` → `/build` → `/verify` → `/ship` — implemented in RULES.md and workflow SKILL.md
- **Anti-Model-Slop Rules** — Explicit definition, enforcement protocol, CI impact table
- **CI (Credibility Index) System** — Earn CI through verified task completion; skills blocked at CI < 30
- **Makefile** — Shortcuts: `make live`, `make dream`, `make test`, `make clean`, `make ci-audit`

### Migration

- Skills migrated from flat `.md` to folder structure under `/skills/`
- Old user-data logs archived to `/memory/archived/` (first Dream Cycle)
- VS Code extension templates updated to NEUTRON EVO OS identity
- `extension.ts` rewritten for `neutron-evo-os` command namespace
- `apply-context.sh` and `apply-context.bat` renamed references updated

### Deprecations

- `AI_CONTEXT_MASTER.md` → superseded by SOUL.md + MANIFESTO.md
- `CH.md` (Context Hub guide) — removed from auto-inject list
- Flat skill files — migrated to `/skills/core/<name>/SKILL.md`
