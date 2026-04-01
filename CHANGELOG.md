# Changelog — NEUTRON EVO OS

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [4.3.0] — 2026-04-01 — Phase 7 Complete

### New Features

- **HTTP MCP Transport** (`mcp_server/http_transport.py`) — FastAPI server on port 3100 with full JSON-RPC 2.0 support. Enables Cursor, Cline, and any HTTP-capable MCP client.
- **MCP Authentication** (`mcp_server/auth.py`) — `X-NEUTRON-API-Key` header validation with token-bucket rate limiting (60 req/min per key).
- **Multi-NEUTRON_ROOT** (`mcp_server/config.py`) — API keys map to specific `NEUTRON_ROOT` paths. Serve multiple projects with one MCP server.
- **Cursor IDE Integration** (`cursor-extension/`) — MCP config + TypeScript plugin + `install-cursor.sh` for one-command Cursor setup.
- **Cline Integration** (`cline-plugin/`) — MCP config + setup script for VS Code Cline extension.
- **Learned Skills Pipeline** (`engine/learned_skill_builder.py`, `skills/learned/`) — Auto-distill patterns from session memory → reusable skills. Lifecycle: learned (CI=35) → proven (CI≥50) → core (CI≥70).
- **`make install-cursor`** — Cursor IDE install target.
- **`make install-cline`** — Cline install target.
- **`make mcp-server`** — Start HTTP MCP server on port 3100.
- **`--transport http`** — New CLI flag for `python3 -m mcp_server`.

### Bug Fixes

- **Config auto-create** — `memory/.mcp_config.json` now auto-creates on first HTTP server start (was silently skipped).
- **`_load()` race condition** — Fixed `_load()` returning empty config without persisting default.

### Documentation

- **ARCHITECTURE.md** — Added MCP HTTP transport, Cursor/Cline, Learned Skills sections. Phase roadmap updated.
- **README.md** — Added IDE Integrations section (Cursor, Cline, MCP server).
- **skills/learned/** — First learned skill: `auto-confirm-skill-level` (captured from Phase 6 fix).
- **skills/core/SKILL.md** — Added auto-confirm FIRST STEP enforcement at documentation level.

---

## [4.2.0] — 2026-04-01 — Phase 6 Complete

### New Features

- **Full skill logic implementations** — All 5 core skills (context, memory, workflow, engine, checkpoint) now have complete `logic/__init__.py` and `validation/__init__.py`.
- **MCP Server** (`mcp_server/`) — Complete stdio JSON-RPC 2.0 server exposing 10 MCP tools, 2 resources (`memory://today`, `ledger://ci`), and 6 workflow prompts. Ready to wire into Claude Code MCP.
- **`neutron` CLI** — `neutron auto`, `neutron audit`, `neutron checkpoint`, `neutron memory`, `neutron log`, `neutron decisions`, `neutron route`, `neutron dream`.
- **`make dream`** — Triggers Dream Cycle (archive + prune + distill).
- **`make ci-audit`** — Full CI health check with skill-by-skill breakdown.
- **Phase 7 foundation** — MCP server structure ready for authentication, HTTP transport, multi-project support.

### Bug Fixes

- **`distill_log()` false positive** — Removed `"|"` from keyword filter (matched all markdown table rows).
- **`extension.ts triggerDream()`** — Wired to `make dream` in terminal (was previously no-op message box).

### Verification

- All 7 skills: `has_logic() = True` ✅
- MCP server: stdio JSON-RPC responds correctly to `tools/list` ✅
- `skill_execution.run()` pipeline: memory + workflow + engine all return valid `{status, ci_delta}` ✅
- CI audit: `overall_ci = 50.0`, all 7 skills healthy ✅

---

## [4.1.0] — 2026-03-30

### New Features

- **`install-global.sh`** — System-wide installer: applies NEUTRON EVO OS context to ALL projects (current & future). Sets up `~/.claude/settings.json`, `~/.claude/CLAUDE.md`, `~/.neutron-evo-os/`.
- **`make install-global`** — `Makefile` target that runs `install-global.sh`.
- **`~/.claude/CLAUDE.md`** — Global fallback context loaded automatically by Claude Code at every session start.
- **`~/.claude/settings.json` global setup** — SessionStart hook + PreToolUse backup hook applied globally. NEUTRON_ROOT env var set.
- **VS Code Extension v4.1.0** — New commands: `NEUTRON EVO OS: Install Globally`, `NEUTRON EVO OS: Status`, `NEUTRON EVO OS: Dream Cycle`. Fixed config keys (`neutronEvoOs.*` vs old `aiContextMaster.*`). Added MANIFESTO.md, START.md, WORKFLOW.md, PERFORMANCE_LEDGER.md to default inject list.

### Improvements

- VS Code Extension: config keys aligned (`neutronEvoOs.*` consistently)
- VS Code Extension: command names prefixed with `NEUTRON EVO OS:` category
- VS Code Extension: embedded templates include full ∫f(t)dt philosophy stubs
- VS Code Extension: `templateSource=external` mode loads real files from NEUTRON_ROOT
- VSIX package rebuilt: `neutron-evo-os-4.1.0.vsix`

### Bug Fixes

- **install-global.sh auto-apply**: Now STEP 6 scans `/mnt/data/projects/*` for existing projects with CLAUDE.md and copies missing NEUTRON files (MANIFESTO.md, WORKFLOW.md, COORDINATION.md, PERFORMANCE_LEDGER.md, MEMORY.md, START.md). Creates `memory/` and `memory/archived/` if missing.
- **PreLoadMemory hook**: Fixed loading only 3 files → now loads all 9 context files.

### Documentation

- README updated with System-Wide Installation section at top
- Architecture diagram updated to show `install-global.sh` and `vscode-extension/`

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
