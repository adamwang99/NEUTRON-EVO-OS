# Changelog — NEUTRON EVO OS

All notable changes are documented here. The format follows [Keep a Changelog](https://keepachangelog.com/).

---

## [4.5.2] — 2026-04-06 — Adversarial Audit R2: P0 + P1 Bug Fixes

### P0 Fixes

- **CRITICAL: `memory._approve_pending` deadlock + lock leak** — Every early return (`target_block is None`, `filelock.Timeout`) leaked one or both of `pending_lock` + `learned_lock`. Concurrent callers would hang forever. Fixed: explicit `acquire()` before `try`, `release()` for both locks in `finally` with `RuntimeError` guard. Consistent lock-order (pending < learned) prevents deadlocks.
- **CRITICAL: `workflow._step_verify` dead code** — `import re` was missing. The entire coverage-parsing block raised `NameError` at runtime. Fixed: `import re` added.

### P1 Fixes

- **CRITICAL: Discovery gate bypass** — Old DISCOVERY.md anywhere on disk caused silent auto-complete. Now scoped to matching `session.json` slug for current task. Explicit `approved=True` bypasses gate (user assumes responsibility).
- **`acceptance_test._save_status`** — Added filelock + atomic write. Concurrent workflow + skill writes no longer lose status data.
- **`discovery._save_session`** — Added per-session filelock + atomic write. Concurrent sessions no longer interleave.
- **`orchestration._save_state`** — Added filelock + atomic write. Systematic fix applied to all 3 state-writing functions.

### Tests

- `test_workflow_spec`: updated for `"blocked"` status (discovery gate enforced, no silent bypass)
- `test_workflow_spec_with_approval`: `approved=True` bypasses discovery gate
- `test_dream_engine`: stale lock cleanup moved to autouse fixture (cross-test isolation)

---

## [4.5.1] — 2026-04-06 — Adversarial Audit R2: HIGH/MEDIUM Hardening

### Security Hardening

- **HIGH: `hooks/dangerous-actions-blocker.sh` rm bypass (R1)** — Word-based parsing replaces broken regex; `rm -rf./path`, `ddif=data`, system-dir `cp/mv` now blocked correctly.
- **HIGH: `build-error-resolver` allowlist bypass** — `shutil.which()` validates binary resolves to a standard bin path (`/usr/bin`, `/usr/local/bin`, `/snap/bin`, `/opt`). `/tmp/evil/pytest` bypass now rejected.
- **MEDIUM: `session-start.sh` Python injection** — Replaced `open('$SNAPSHOT')` in `-c` string with a temp Python script (`mktemp` + heredoc). SNAPSHOT path can no longer inject Python code.
- **MEDIUM: `session-end.sh` zombie prevention** — `nohup bash -c "..." & disown` replaces bare `&`. Background children survive parent exit without becoming zombies.

### Process Safety

- **CRITICAL: `config.py` filelock** — `_save()` now uses filelock + atomic write; concurrent config writes no longer corrupt `memory/.mcp_config.json`.
- **CRITICAL: `checkpoint_cli.py` filelock** — `_write_atomic()` with filelock added; concurrent checkpoint writes no longer interleave.
- **HIGH: `learned_skill_builder._record_invocation()`** — Filelock wraps entire load→save cycle; concurrent invocations no longer silently lose counts.

### Resource Management

- **MEDIUM: `auth.py` rate bucket leak** — TTL eviction (60s idle) + hard cap (10K entries) + lazy cleanup every 1000 calls. Unbounded memory growth from guessed API keys eliminated.
- **HIGH: `mcp_server/auth.py` timing attack** — Dummy `hmac.compare_digest()` runs even when header is absent, making execution time identical for "no key" vs "wrong key".

### Information Disclosure

- **HIGH: `/ready` endpoint** — Removed `engine_found` boolean that leaked existence of `engine/` directory. Now returns only `{"status": "ok"}`.
- **HIGH: `hooks/pretool-backup.sh` option injection** — `realpath -- FILEPATH` now stops option parsing; `FILEPATH="--relative-to=/etc /etc/passwd"` no longer injects realpath options.

### Crash Safety

- **CRITICAL: `dream_engine._write_cookbook()`** — Cookbook now uses `_atomic_write()` instead of plain `write_text()`.
- **CRITICAL: `dream_engine` Phase 5 log truncation** — Active log truncation now uses `_atomic_write()`.
- **HIGH: `skill_execution._write_execution_log()`** — `Timeout: pass` replaced with `logger.warning()` so lock contention is detectable.

### Test Infrastructure

- **`tests/test_dream_engine.py`** — `autouse` fixture clears `_DREAM_LOCK_CACHE` + removes stale `memory/.dream.lock` before each test; prevents cross-test lock pollution.

---

## [4.5.0] — 2026-04-06 — Adversarial Audit Round 2

### Security Fixes

- **CRITICAL: `hooks/dangerous-actions-blocker.sh` rm bypass** — Regex `^[[:space:]]*(sudo[[:space:]]+)?rm[[:space:]]+(-[rf]+\s+)?...` required whitespace after `-rf` flags. `rm -rf./file` bypassed detection. Fixed: word-based pattern detection parses command into individual words, checks `rm` + `-rf`/`-r`+`-f` combos independently. Also fixed `dd` block (no space required for `of=`), system-dir `cp/mv` (word-by-word scan), and `find -delete` patterns.
- **CRITICAL: `mcp_server/auth.py` timing attack** — Missing header returned `False` immediately; invalid header ran `hmac.compare_digest` (slow). Timing delta revealed key presence. Fixed: always execute dummy `hmac.compare_digest` on empty path, making execution time identical.
- **CRITICAL: `skills/core/memory` path traversal** — `_archive_file()` accepted any readable path (`../../../etc/passwd`) and archived it into `memory/archived/`. Fixed: `p.resolve().relative_to(_NEUTRON_ROOT)` validates path stays inside project.

### Concurrency Fixes

- **CRITICAL: `mcp_server/config.py` filelock** — `_save()` was unwritten. Concurrent `_load()` → `_save()` races could corrupt `memory/.mcp_config.json`. Fixed: filelock + atomic write (temp file + fsync + rename).
- **CRITICAL: `engine/checkpoint_cli.py` unwritten writes** — `checkpoint_path.write_text(new_content)` had no filelock. Concurrent `neutron checkpoint` calls from multiple sessions interleaved writes. Fixed: `_write_atomic()` with filelock + atomic write.
- **CRITICAL: `engine/dream_engine.py` unwritten Phase 5 writes** — `_write_cookbook()` and active log truncation used plain `write_text()`. Dream Cycle crash mid-write left log corrupted. Fixed: both use `_atomic_write()`.

### Crash Safety

- **HIGH: `engine/skill_execution.py` silent log loss** — `except Timeout: pass` in `_write_execution_log()` silently dropped audit trail when filelock timed out. Fixed: `logger.warning()` so contention is detectable, not invisible.

### Test Infrastructure

- **FIX: `tests/test_dream_engine.py` lock pollution** — `autouse` fixture now clears `_DREAM_LOCK_CACHE` before/after each test AND removes stale `memory/.dream.lock` files. Prevents cross-test lock state pollution.

---

## [4.4.0] — 2026-04-06 — Adversarial Audit + Regression Guard + P0 Security Fixes

### New Features

- **Regression Guard** (`engine/regression_guard.py`) — Anti-regression system:
  - Golden snapshot: record outputs of 2 deterministic skills + 9 critical imports
  - Smoke test: runs on every edit to `engine/*`, `skills/*`, `mcp_server/*`
  - Regression check: compares fingerprints vs baseline, blocks on crash/status-change
  - `neutron regress --snapshot` (establish baseline), `neutron regress --check` (run check)
  - PreToolUse hook updated: backup → smoke test → regression check in 2 phases

- **Context 30-Day Limit** (`skills/core/context/logic/__init__.py`) — `_estimate_context_size()` now limits scan to last 30 days only, preventing memory exhaustion on repos with years of daily logs

- **Go Reviewer Package Filter** (`skills/core/go-reviewer/logic/__init__.py`) — Fixed `go vet ./...` hardcode; now builds package list from actual file paths

- **Workflow Subprocess Crash Guard** (`skills/core/workflow/logic/__init__.py`) — Added `try/except FileNotFoundError` around pytest invocation

### Bug Fixes

- **CRITICAL: `rating.py` lost-update race** — `_load()` then `_save()` without lock. Concurrent `record_shipment()` calls from different processes could lose updates. Fixed: `_atomic_update()` wraps entire read-modify-write in a single filelock.

- **CRITICAL: `dangerous-actions-blocker.sh` argument parsing broken** — `_shift "$#"; shift` compound command always emptied `$_cmd`, silently bypassing ALL protection for every Bash command. Fixed: proper manual argument parsing.

- **CRITICAL: `auth.py` stale API key cache** — `resolve_neutron_root()` cached key→root mappings forever, so revoked keys remained active until server restart. Fixed: removed cache, re-validate against config every call.

- **CRITICAL: `learned_skill_builder.py` broken generated code** — Literal `"{slug}"` string generated instead of variable `slug`. Fixed: proper variable interpolation.

- **HIGH: `memory/logic` duplicate `_append_decisions`** — Second definition shadowed first, using `id: 0` for all synced decisions instead of unique IDs. Second definition removed.

- **HIGH: `http_transport.py` CORS wildcard fallback** — If `config.get_server_config()` returned `{}`, CORS defaulted to `["*"]`. Fixed: explicit localhost-only fallback.

- **HIGH: `auto_confirm.py` filelock deadlock** — `should_skip()` called `record_auto_action()` while still holding lock, which called `_log_auto_action()` trying to acquire same lock again. Fixed: separate nested function, release lock before calling `_log_auto_action()`.

### Security Improvements

- **`hooks/dangerous-actions-blocker.sh`** — Replaced broken negative lookahead grep with POSIX-compatible patterns; fixed `--force-with-lease` vs `--force` detection; fixed SSH unknown-host extraction
- **`mcp_server/auth.py`** — Removed stale key cache (revocation now immediate); removed deprecated `set_neutron_root_for_key()`
- **`mcp_server/http_transport.py`** — API key timing-safe comparison noted; CORS fallback hardened

### Architecture

- **Regression Guard preToolUse integration**: `hooks/pretool-backup.sh` now runs 2-phase protection (backup + smoke test) for `engine/*`, `skills/*`, `mcp_server/*` file writes
- **Auto-confirm deadlock fix**: `_should_skip_impl()` isolates lock-protected read, releases before `_record_auto_action()`

### Tests
- **78/78 pass** ✅
- **Regression guard: clean** ✅

---

## [4.3.2] — 2026-04-01 — Garbage Collection + Session-Start Fix

### New Features

- **`neutron gc`** (`engine/cli/main.py`) — Garbage collection CLI command với nhiều flags:
  - `--retention N` — archived/ retention in days (default: 7)
  - `--backup-days N` — .backup/ retention in days (default: 30)
  - `--pycache` — delete __pycache__ and *.pyc
  - `--tests` — delete pytest cache
  - `--large MB` — delete files larger than N MB
  - `--empty` — remove empty directories
  - `--data-json` — delete data_*.json dumps in archived/
  - `--dry-run` — preview without deleting

- **Session-start auto-GC** (`hooks/session-start.sh`) — GC chạy tự động mỗi khi Claude Code khởi động:
  - archived/ logs > 7 ngày
  - `__pycache__/`, `*.pyc`, `.pytest_cache`
  - `data_*.json` dumps in archived/

- **Session-start hook fix** — Eliminated `command_substitution` security prompt:
  - Extracted inline Python heredoc → `hooks/neutron-first-run.py`
  - Pre-approved permission trong Claude Code settings

- **CLAUDE.md update** — Full quick reference với tất cả commands

### Disk Usage

- Cleaned 60K+ garbage files
- Total disk: **481 MB → 252 MB (-48%)**

---

## [4.3.1] — 2026-04-01 — Audit Fixes + UI Library + CLI Upgrade

### New Features

- **UI Library Reference Skill** (`skills/core/ui_library/`) — Auto-suggest best UI library (shadcn/ui, AntD, Mantine, Magic UI, DaisyUI) dựa trên project type, tech stack, và requirements. Tích hợp vào `/spec` step.
- **`neutron version`** (`engine/cli/main.py`) — Hiển thị version, health, CI, ratings, auto-confirm status.
- **`neutron protect [--dry-run]`** (`engine/cli/main.py`) — Backup `.env`, `memory/*.json`, `USER.md` → `.backup/`.
- **USER.md** (`memory/USER.md`) — User preferences file, được tạo từ template với UI và versioning preferences.
- **Upgrade Protection Protocol** (`RULES.md`) — MANDATORY steps trước mọi upgrade: git status + backup.

### Bug Fixes

- **Auto-confirm enforcement** (`discovery/SKILL.md`, `workflow/SKILL.md`, `acceptance_test/SKILL.md`, `SOUL.md`) — Root cause: Claude Code đọc SKILL.md như TEXT, không execute Python. Viết lại SKILL.md với hard-line directive language (STEP 1-4 decision tree, "SKIP EVERYTHING" checklist).
- **SPEC gate auto-bypass** (`workflow/SKILL.md`) — AUTO-CONFIRM BYPASS block trước USER REVIEW gate.
- **Acceptance gate auto-bypass** (`workflow/SKILL.md`, `acceptance_test/SKILL.md`) — AUTO-CONFIRM BYPASS block trước USER TEST gate.
- **PII redaction over-match** (`checkpoint_cli.py`) — Phone pattern match cả API key. Fix: đưa specific key pattern (sk-, ghp_, xox-) lên TRƯỚC phone pattern.
- **Auto-confirm Python TypeError** (`discovery/logic/__init__.py`) — `_save_session()` gọi sai signature → silent TypeError swallowed → auto-confirm không hoạt động. Fix: đúng 4 positional args.
- **Rating not saved** (`workflow/logic/__init__.py`) — `_step_ship()` không call `rating.record_shipment()`.
- **CORS security** (`mcp_server/http_transport.py`) — `allow_credentials=True` + `allow_origins=["*"]` bị browser reject.
- **Multi-tenant race** (`http_transport.py`) — `os.environ` bị mutate per-request. Giờ dùng `contextvars.ContextVar`.
- **Rate limit bypass** (`http_transport.py`) — `/keys` endpoints không check rate-limit. — MANDATORY steps before any upgrade
  (`git pull`, `pip install`, `install.sh`, etc.):
  - Check `git status` first
  - Backup protected files (`.env`, `memory/*.json`, `USER.md`) to `.backup/`
  - Use `git checkout --ours` for local data files that git also tracks
  - Verify `.gitignore` covers all data files
  - Restore from `.backup/` if data is lost after upgrade

### Bug Fixes

- **CORS security** (`mcp_server/http_transport.py`) — `allow_credentials=True` với `allow_origins=["*"]` bị browser reject. Giờ dùng config `cors_origins`, credentials=False
- **Multi-tenant race** (`http_transport.py`) — `os.environ["NEUTRON_ROOT"]` bị mutate per-request gây race condition. Giờ dùng `contextvars.ContextVar`
- **Rating not saved** (`workflow/logic/__init__.py`) — `_step_ship()` không call `rating.record_shipment()` hay `add_rating()`. Giờ có rồi
- **Learned skill invocation** (`skill_execution.py`) — sai import path (`skills.core.learned` vs `skills.learned.<slug>`). Giờ detect qua registry đúng
- **Config data destruction** (`config.py`) — `_load()` overwrite file corrupted không backup. Giờ backup vào `.config_backup/` trước
- **Session-start checkpoint path** (`session-start.sh`) — đọc `memory/.last_checkpoint.md` (file không tồn tại). Giờ đọc từ daily log
- **Acceptance test auto-confirm** (`acceptance_test/logic/__init__.py`) — thiếu FIRST STEP check. Giờ check `should_skip("acceptance")` ngay đầu function
- **Duplicate `_record_invocation()`** (`learned_skill_builder.py`) — dead code ở line 438. Đã xóa
- **Rate limit bypass** (`http_transport.py`) — `/keys` endpoints không check rate-limit. Giờ check rồi
- **UnicodeDecodeError unhandled** (`transport.py`) — invalid UTF-8 stdin crash. Giờ handle rồi
- **Missing engine exports** (`engine/__init__.py`) — thiếu 5 modules trong `__all__`. Giờ export đủ
- **Silent audit log failure** (`auto_confirm.py`) — `_log_auto_action()` silent pass on error. Giờ print stderr

### Improvements

- **`.gitignore`** — thêm `memory/shipments.json`, `memory/user_decisions.json`, `memory/.mcp_config.json`, `memory/.auto_confirm.json`, `memory/handoff*.md`, `.backup/` để không bao giờ commit user data
- **CLI docstring** (`engine/cli/main.py`) — bỏ `neutron explore` không tồn tại, sửa typo
- **Workflow SKILL.md** — thêm `/verify` vào step table
- **`pretool-backup.sh`** — portable `NEUTRON_ROOT` thay vì hardcode path

### Tests

- **70/70 pass** (trước: 69/70) — `test_workflow_spec_returns_proper_status` giờ accept 3 states: `spec_written`, `awaiting_discovery`, `spec_approved`

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
