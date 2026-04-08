# LEARNED.md — Bug Fixes & Pattern Database

> Every bug fix is a permanent asset. Every mistake is a lesson learned.
> ∫f(t)dt — Functional Credibility Over Institutional Inertia

---

## [2026-04-08] Bug: Orchestrator execute phase only generated text configs — no real agents

- **Symptom:** NEUTRON claimed "parallel N-agent swarm execution" but the orchestration
  `execute` phase returned text `Agent(...)` configs that Claude Code had to manually
  copy-paste and run. No actual agent spawning occurred. True parallelism only existed
  in `mcp_server/tools.py::spawn_parallel()` but it was never called by the orchestrator.
- **Root cause:** Orchestrator's `execute` phase built agent configs and returned them
  as text blocks for manual spawning, instead of calling `spawn_parallel()`. The
  `max_workers=1` in `_spawn_agent()` also made even the MCP layer sequential.
- **Fix:**
  - `engine/orchestration_spawn.py`: **NEW** — dedicated parallel spawn engine.
    Exports `spawn_parallel_agents()` and `spawn_single()` using Claude Agent SDK.
    max_workers=n (not 1) for true parallelism.
  - `skills/core/orchestration/logic/__init__.py`: execute phase now calls
    `spawn_parallel_agents()` directly and auto-advances to merge. Fallback text
    mode only if `claude-agent-sdk` not installed.
  - `mcp_server/tools.py`: already correct (max_workers=n in spawn_parallel).
- **Tags:** `#orchestration` `#swarm` `#parallel`
- **Lesson:** A feature that generates text configs instead of calling real functions
  is not a real feature. "Spawning now" in the output text ≠ actual spawning.

---

## [2026-04-08] Bug: NEUTRON claimed 5 capabilities but only 1 was real

- **Symptom:** NEUTRON CLAUDE.md listed 5 core capabilities:
  (1) Coding speed, (2) Swarm agents, (3) UI skill integration, (4) 3-tier memory, (5) Learning system.
  Full audit revealed: 1 fully working, 4 partial, 0 fake (no outright lies), but all had gaps.
- **Root cause:** Multiple architectural gaps accumulated over development:
  (a) Build step was scaffolding-only (no actual code gen), (b) Orchestrator was text-generator not real spawner,
  (c) Cookbooks written but never read, (d) Learned skills were no-op stubs, (e) regression_guard.py existed but not wired.
- **Fix:** Systematically fixed 8 gaps:
  - `engine/orchestration_spawn.py`: true parallel spawn ✅
  - `skills/core/orchestration/logic/__init__.py`: wired to spawn_parallel ✅
  - `hooks/active-recall.py`: added `.active_recall.json` for context injection ✅
  - `skills/core/memory/logic/__init__.py`: 3-tier search (SHORT/MID/LONG) ✅
  - `skills/core/workflow/logic/__init__.py`: regression guard integration ✅
  - `memory/cookbooks/`: cleaned tmp* garbage, removed test cookbooks ✅
  - `memory/pending/LEARNED_pending.md`: truncated 26MB duplicate → clean file ✅
- **Tags:** `#audit` `#architecture` `#claims-vs-reality`
- **Lesson:** CLAUDE.md claims must match implementation reality. "Partial" features
  create false confidence. Regular adversarial self-audit is required.

---

## [2026-04-08] Bug: Cross-Project Read Access — No Boundary Enforcement

- **Symptom:** While working in `/mnt/data/projects/ant-downloader/`, Claude Code
  read files from `/mnt/data/projects/octa/` (cross-project boundary breach):
  `octa/memory/LEARNED.md`, `octa/server/backtest/backtestEngine.ts`, etc.
  Neither `ant-downloader` nor `octa` has NEUTRON EVO OS installed — the breach
  came from Claude Code's own Read tool.
- **Root cause:** NEUTRON EVO OS had **zero enforcement** on Read/Glob/Grep
  operations. The system only protected Write/Edit via `pretool-backup.sh` (PreToolUse
  hook with `matcher: "Edit|Write"`). Read/Glob/Grep were completely ungoverned.
  No settings.json path deny rules existed. CLAUDE.md boundary directives were
  advisory only.
- **Fix:**
  1. `hooks/pretool-guard.sh`: **NEW** — PreToolUse hook for Read/Glob/Grep.
     Validates absolute paths stay within CWD or NEUTRON_ROOT. Blocks with
     clear error + MCP tool suggestions.
  2. `~/.claude/settings.json`: Added PreToolUse hook entry for `Read|Glob|Grep`
     → `pretool-guard.sh`. Guards now active system-wide.
  3. `engine/path_validation.py`: **NEW** — Python boundary utility. Exports
     `enforce_boundary()`, `check_boundary()`, `BoundaryViolation`. Importable
     by all skills.
  4. All project CLAUDE.md files updated: `ant-downloader/`, `octa/`, `Web2md/`,
     `ai-context-master/` (hub) — added "Directory Boundary" section.
  5. `memory/pending/`: Cleaned 49 garbage tmp* files (~600MB), kept LEARNED_pending.md.
- **Tags:** `#boundary` `#security` `#pretool` `#hook`
- **Lesson:** CLAUDE.md directives are advisory, not enforced. A real security
  boundary requires a PreToolUse hook that fires on Read/Glob/Grep, not just
  Edit/Write. The lesson from yesterday's `_record_decision` guard (NEUTRON_DREAM_TEST=1)
  applies here too: any side-effect or access operation needs an active guard.
> ∫f(t)dt — Functional Credibility Over Institutional Inertia

---

## [2026-04-07] Bug: ((OK++)) with set -e causes silent exit 1

- **Symptom:** `install.sh` ran every step successfully but always exited with code 1
  even though all verifications passed. Users saw "[OK]" everywhere then "exit 1".
- **Root cause:** `set -euo pipefail` in install.sh + `((OK++))` when `OK=0`. In bash,
  `((expr))` returns 1 (failure) when the result of the expression is 0. `((0++))`
  evaluates to 0 → bash sets exit status to 1 → `set -e` aborts the script.
  Since `((OK++))` was the last statement of the if-block, the `else` was never
  reachable when the test passed — making the bug invisible in normal runs.
- **Fix:** Changed `((OK++))` → `((OK++)) || true` at lines 294 and 309.
- **Tags:** `#bash` `#set-e` `#arithmetic`
- **Lesson:** Never use `((var++))` as the last statement of a `set -e` block when
  `var=0`. The post-increment expression evaluates to 0 → exit 1.

---

## [2026-04-07] Bug: SessionStart hook FD deadlock — every session exit 1

- **Symptom:** Every Claude Code session showed "SessionStart: startup hook error" even
  though the hook script completed its work. Exit code was 1.
- **Root cause:** `session-start.sh` line 81 opened FD 200 in the **parent** shell
  (`exec 200>"$GC_LOCK"`) before the subshell that calls `flock -n 200`. Since the
  parent held the FD open, `flock -n 200` inside the subshell always saw a conflicting
  lock on the same FD and immediately failed. The subshell exited 1, propagating to
  the whole script.
- **Fix:** Moved FD 200 entirely inside the subshell. The subshell now holds the lock
  exclusively for its lifetime; the parent never holds it open. Parent's exit code
  reflects subshell's success.
  - `hooks/session-start.sh:78-103`: Restructured GC flock block so the subshell
    acquires and releases the lock, not the parent.
- **Tags:** `#hook` `#flock` `#fd-leak`
- **Lesson:** `flock -n` inside a subshell cannot succeed if the parent has the same FD
  open. Always keep the FD acquisition inside the subshell that needs the lock.

---

## [2026-04-07] Enhancement: install.sh — add mcpServers for new users

- **Symptom:** New users running `install.sh` got hooks configured but no `mcpServers`
  entry. MCP tools (neutron_memory, neutron_workflow, etc.) silently failed with
  "No module named mcp_server" when Claude Code started in any project directory.
- **Root cause:** `install.sh` step 6 only wrote `hooks` to `settings.json`, omitting
  the `mcpServers` block. Users had to manually add the MCP server config.
- **Fix:** Added MCP server registration in `install.sh` step 6 — `setdefault("mcpServers", {})`
  merge preserves any existing MCP servers the user already has. `NEUTRON_ROOT` is set
  to the dynamic `install_dir`, not hardcoded.
  - `install.sh:244-266`: `settings.setdefault("mcpServers", {})["neutron-evo-os"] = _mcp_config`
- **Tags:** `#packaging` `#mcp` `#install`
- **Lesson:** Every capability the installer enables must be registered in settings.json,
  not assumed to be handled by the user's existing config.

---

## [2026-04-07] Bug: install.sh destroyed existing Claude Code hooks from other tools

- **Symptom:** Running `install.sh` would silently overwrite the user's entire
  `settings["hooks"]` object, deleting any `SessionStart` or `PreToolUse` hooks
  from other Claude Code plugins or tools.
- **Root cause:** `install.sh` step 6 assigned `settings["hooks"]["SessionStart"] = [...]`
  and `settings["hooks"]["PreToolUse"] = [...]` directly, replacing the whole array
  instead of appending.
- **Fix:** Replaced direct assignment with `_add_hook_if_missing()` helper that checks
  for duplicate command paths before appending, preserving all existing hooks.
  - `install.sh`: Added `_add_hook_if_missing()` function; SessionStart and PreToolUse
    now use `setdefault()` + duplicate detection instead of overwrite.
- **Tags:** `#packaging` `#hook` `#data-loss`
- **Lesson:** Installer merge logic must preserve existing config, never replace wholesale.

---

## [2026-04-07] Bug: session-start.sh COOKBOOK_DIR undefined — Dream Cycle never fired

- **Symptom:** Dream Cycle auto-trigger never ran on any Claude Code session start,
  even after 12+ hours. The `if [ "$SHOULD_RUN" -eq 1 ] && [ -d "$COOKBOOK_DIR" ]`
  check always failed silently.
- **Root cause:** `COOKBOOK_DIR` was never set anywhere in `session-start.sh`. Bash
  expanded it to an empty string; `[ -d "" ]` is always False, so the entire
  Dream Cycle Python subprocess was dead code.
- **Fix:** Added `COOKBOOK_DIR="$MEMORY_DIR/cookbooks"` before the Dream Cycle block.
  - `hooks/session-start.sh`: `DREAM_LOCK` line, added `COOKBOOK_DIR` assignment.
- **Tags:** `#hook` `#dream-cycle` `#dead-code`
- **Lesson:** Bash undefined variables expand to empty strings silently. Always define
  variables before use, or use `set -u` to catch them.

---

## [2026-04-07] Bug: mcp_server/auth.py nonlocal in module-level function

- **Symptom:** Rate limiter could not be imported — Python raised `SyntaxError:
  nonlocal declaration not allowed at module level`.
- **Root cause:** `nonlocal _eviction_counter` on line 69 of `auth.py`. The variable
  `_eviction_counter` is a module-level global, not a closure variable. `nonlocal`
  is only valid inside nested functions. Using it at module level is always a
  SyntaxError before any code runs.
- **Fix:** Deleted `nonlocal _eviction_counter`. At module level, `_eviction_counter += 1`
  is a plain global mutation — no declaration needed.
  - `mcp_server/auth.py:69`: removed the offending line.
- **Tags:** `#mcp` `#python` `#syntax`
- **Lesson:** `nonlocal` is for closure scopes. `global` is for module-level. Neither
  is needed for simple module-level mutation — just assign directly.

---

## [2026-04-07] Bug: engine/auto_confirm.py write_text inside filelock not atomic

- **Symptom:** `_log_auto_action()` used `path.write_text()` inside a filelock, but
  `write_text()` writes synchronously without fsync. A crash between the lock release
  and disk commit could lose the last logged entry.
- **Root cause:** Filelock protected the read-modify-write sequence, but the actual write
  used `write_text()` which is not atomic on crash. No fsync, no temp file, no rename.
- **Fix:** Replaced `log_path.write_text(content + entry + "\n")` with
  `atomic_write(log_path, content + entry + "\n")` which uses temp file + fsync + rename.
  - `engine/auto_confirm.py:245`: `write_text()` → `atomic_write()`
- **Tags:** `#atomic` `#data-integrity` `#crash-safety`
- **Lesson:** Filelock alone is not sufficient for crash-safety. Every write inside
  a lock must also be atomic (temp+fsync+rename) to survive system crashes.

---

## [2026-04-07] Bug: engine/dream_engine.py lock cache reassigned every call

- **Symptom:** `_DREAM_LOCK_CACHE` was reassigned to a fresh `FileLock` on every call
  to `_get_dream_lock()`. Since `is_locked()` on a new FileLock instance always returns
  False (each instance tracks its own lock state), the re-entrancy guard was broken —
  concurrent dream cycles could start simultaneously.
- **Root cause:** `_DREAM_LOCK_CACHE = _filelock.FileLock(lock_path, timeout=5)` inside
  the function body ran on every call, creating a brand-new lock object each time.
  The old lock's `is_locked()` state was lost.
- **Fix:** Changed to lazy initialization — `_DREAM_LOCK_CACHE` is created once,
  cached, and reused. `_get_dream_lock()` now only creates the lock if `_DREAM_LOCK_CACHE
  is None`.
  - `engine/dream_engine.py:71-79`: lazy init instead of reassign-every-call.
- **Tags:** `#concurrency` `#filelock` `#re-entrancy`
- **Lesson:** Caching a lock object is valid only if the cache is stable across calls.
  Reassigning a new lock every call defeats the purpose of caching entirely.

---

## [2026-04-07] Bug: expert_skill_router false positives on "context" and "engine"

- **Symptom:** The `context` and `engine` skills were routing incorrectly on everyday
  prompts like "fix the context of this email" or "check the engine light" because
  these common English words appear in non-technical sentences.
- **Root cause:** Keywords `"context"` and `"engine"` used `word_boundary=False`,
  matching them anywhere in the text regardless of surrounding word boundaries.
- **Fix:** Changed both to `word_boundary=True` so they only match when surrounded
  by word boundaries, not as substrings of unrelated words.
  - `engine/expert_skill_router.py:153,178`: `("context", False)` → `True`,
    `("engine", False)` → `True`.
- **Tags:** `#routing` `#false-positive` `#keyword`
- **Lesson:** Short generic English words should always use word-boundary matching
  in keyword routers to avoid false positives on casual language.

## [2026-04-05] Bug: Observer scan parent directory — bleed into sibling projects


---



- **Symptom:** Opening a project in a subdirectory caused Claude Code to scan the root
  directory and process sibling projects.
- **Root cause:** `SilentObserver.start()` accepted any `root_path` without validation.
  If caller passed a parent directory, `watchdog` with `recursive=True` would scan
  all subdirectories including sibling projects. Additionally, `SilentObserver.stop()`
  was a global singleton — calling stop() from project A would stop project B's observer.
- **Fix:**
  - `skills/core/engine/logic/__init__.py:58-88`: Added boundary validation before
    starting observer — rejects parent directories and non-project paths.
  - `engine/smart_observer.py:87-182`: Added `_root` tracking field. `stop(root=X)`
    now refuses to stop if the observer is watching a different root.
  - `engine/dream_engine.py:127-129`: Passes `str(NEUTRON_ROOT)` to `stop()` so
    dream cycle only affects its own observer.
  - `hooks/session-start.sh:72`: Added `&& [ -f "$NEUTRON_ROOT/engine/cli/main.py" ]`
    guard so GC only runs when NEUTRON_ROOT is valid.
- **Tags:** `#boundary` `#observer` `#scope-leak`
- **Commit:** `4f01387`

---

## [2026-04-05] Bug: PreLoadMemory in settings.json caused Settings Error

- **Symptom:** `claude` CLI showed "Settings Error — PreLoadMemory: Invalid key in
  record" and skipped the entire settings.json.
- **Root cause:** `PreLoadMemory` is not a valid hook in Claude Code's settings schema.
  The schema defines exactly 22 hook names; `PreLoadMemory` does not exist. The
  original config used a simple array format that doesn't match any valid structure.
- **Fix:**
  - Removed `PreLoadMemory` entirely from `/mnt/data/projects/octa/.claude/settings.json`.
  - Session context now loaded via `SessionStart` hook (type: "command") which echoes
    SOUL.md, MEMORY.md, HEARTBEAT.md into the transcript.
  - Updated `install-global.sh` to no longer reference `PreLoadMemory` as a feature.
- **Tags:** `#settings` `#hook` `#schema`
- **Lesson:** Never use undocumented Claude Code settings keys. Always validate
  against the official JSON schema at json.schemastore.org/claude-code-settings.json.

---

## [2026-04-05] Bug: SilentObserver.stop() global singleton race

- **Symptom:** If two projects run observers simultaneously, calling `stop()` from
  project A would kill project B's observer silently.
- **Root cause:** `SilentObserver` was a true global singleton with no scope tracking.
  `_running` was a class-level boolean shared across all callers. There was no
  mechanism to distinguish "my observer" from "someone else's observer."
- **Fix:** Added `_root: Optional[str] = None` field to track which root path the
  observer was started with. `stop(root=X)` now compares `cls._root != X` and refuses
  with a warning log if they don't match. `stop()` with no argument still works
  for backward compatibility.
- **Tags:** `#threading` `#singleton` `#observer`

---

## [2026-04-05] Bug: session-start.sh GC runs with invalid NEUTRON_ROOT

- **Symptom:** If `NEUTRON_ROOT` env var was misconfigured or empty, the garbage
  collection `find` commands would scan the wrong directory.
- **Root cause:** The GC block only checked for a lock file (`$GC_LOCK`) but not
  whether `$NEUTRON_ROOT` was a valid NEUTRON installation.
- **Fix:** Added guard: `if [ ! -f "$GC_LOCK" ] && [ -f "$NEUTRON_ROOT/engine/cli/main.py" ]`
  — GC only runs when NEUTRON_ROOT points to a real NEUTRON installation.
- **Tags:** `#gc` `#env-var` `#boundary`

---

## Pattern: How to Record a New Learning

When you fix a bug or discover a pattern:

1. Add a new section to this file following the template above.
2. Fill in: date, symptom, root cause, exact fix (file:line), tags.
3. Commit with message: `fix: add LEARNED.md entry for <bug description>`
4. Search past learnings: `grep -i "<tag>" memory/LEARNED.md`

---

## Tags Reference

| Tag | Meaning |
|-----|---------|
| `#boundary` | Path/directory scope issues |
| `#observer` | SilentObserver, watchdog, file watching |
| `#gc` | Garbage collection, cleanup |
| `#hook` | Claude Code hooks, settings.json |
| `#threading` | Concurrency, race conditions |
| `#schema` | JSON validation, config format |
| `#mcp` | MCP server, tools, resources |
| `#security` | Auth, permissions, access control |
| `#performance` | Speed, memory, optimization |

---

*Last updated: 2026-04-07*
*Auto-archived from: memory/YYYY-MM-DD.md sessions*

## [2026-04-05] Bug: Decisions from trading-bot mixed into NEUTRON project

- **Symptom:** memory/user_decisions.json had 2 pending decisions about
  trading-bot (SPEC approved, Python+Binance) that were pending for 5 days,
  but NEUTRON EVO OS doesn't build trading bots.
- **Root cause:** A previous session recorded decisions without scoping
  them to the correct NEUTRON_ROOT. Decisions from project A ended up
  in project B's memory/ file.
- **Fix:** Archived misplaced decisions to memory/archived/decisions_misplaced_*.json,
  reset user_decisions.json to []. Decisions now scoped per project by MEMORY_DIR.
- **Tags:** #boundary #memory #scope
- **Lesson:** Decisions must be scoped to the correct project root. Each project
  should have its own memory/ directory with its own user_decisions.json.

## [2026-04-05] Bug: decisions/shipments.json had no file locking

- **Symptom:** Concurrent sessions writing to user_decisions.json or shipments.json
  could silently overwrite each other's data. JSON could become invalid on collision.
- **Root cause:** Read-modify-write on both files had no synchronization.
  No filelock, no atomic write. Session A reads, Session B reads, both write,
  one overwrite the other.
- **Fix:** Added _locked_read_write() helper using filelock.FileLock with 10s timeout.
  All read-modify-write on decisions/shipments now uses filelock + atomic write.
  ()
- **Tags:** #concurrency #data-corruption #filelock
- **Lesson:** Any shared JSON file written by multiple processes needs filelock.

## [2026-04-05] Bug: pre-commit LEARNED-check hook was a no-op

- **Symptom:** check-learned-entry.py always returned True (exit 0), even for
  fix: commits without LEARNED.md entries. No enforcement.
- **Root cause:** Comment said "change to sys.exit(1) for hard requirement"
  but the code was never updated. Developer could skip LEARNED.md entirely.
- **Fix:** Changed to sys.exit(1) — HARD BLOCK on fix: commits without LEARNED.md entry.
- **Tags:** #hook #enforcement
- **Lesson:** Warning-only hooks are not enforcement. If a rule exists, it must block.


---

## [2026-04-08] Bug: Shipments & Decisions tracking never activated

- **Symptom:** `memory/shipments.json` and `memory/user_decisions.json` were empty
  (117 decisions but no user decisions, 2 shipments but no shipments records).
  `record_shipment()` existed in `_step_ship()` but no workflow ever ran through
  `/ship`. `user_decisions.record()` existed but was never called anywhere.
- **Root cause:** Two-part failure:
  1. Shipments: `_step_ship()` called `record_shipment()` correctly, but the
     complete workflow (`/explore → /discovery → /spec → /build → /acceptance → /ship`)
     was never run end-to-end. Shipments existed in one-off test calls only.
  2. Decisions: `user_decisions.py` was a complete, well-written module but
     was never imported or called from any skill or workflow step. RULE 3
     specified the requirement but no code implemented it.
- **Fix:**
  - `skills/core/workflow/logic/__init__.py`: Added `_record_decision()` helper
    that calls `user_decisions.record()` with best-effort error handling.
    Called automatically in:
    - `_step_discovery()` (auto-confirm path): "Discovery auto-confirmed"
    - `_record_spec_approval()`: "SPEC approved" / "SPEC changes requested"
    - `_step_ship()`: "Project shipped"
  - `hooks/gc_lightweight.py`: `MAX_ARCHIVED=500` → 100, added compression of
    old files (files older than 3 days → tar.gz). Archived/ shrunk from
    500 files (3.2MB) to 24 files + 1 tar.gz (72KB) — 98% reduction.
- **Tags:** `#workflow` `#memory` `#data-integrity` `#rule-3`
- **Lesson:** Module existence ≠ feature activation. A well-written module that
  is never called is the same as no module. Every CLAUDE.md RULE must have
  implementation code that enforces it, not just documentation.


---

## [2026-04-08] Bug: _record_decision called in test mode — decision spam

- **Symptom:** 1190 "SPEC approved for build" entries in user_decisions.json.
  `user_decisions.json` grew from 2 to 1190+ entries during development,
  all identical, all from test runs.
- **Root cause:** `_record_decision()` had no test-mode guard. Each test run
  of `test_workflow_spec_*` triggered `_record_spec_approval()` → `_record_decision()`.
  `conftest.py` sets `NEUTRON_DREAM_TEST=1` to block dream cycles, but
  `_record_decision` didn't check this env var.
- **Fix:** `_record_decision()` now checks `NEUTRON_DREAM_TEST=1` and returns
  early. Test pollution stopped. Cleanup: deduped to 2 unique entries.
  - `skills/core/workflow/logic/__init__.py`: added env guard.
- **Tags:** `#workflow` `#test-pollution` `#decision`
- **Lesson:** Any side-effect function (writes to disk, state files) needs a
  test-mode guard. conftest.py's `NEUTRON_DREAM_TEST` must be respected
  by ALL state-writing functions, not just dream_engine.

---

## [2026-04-08] Enhancement: Active Recall — PreToolUse LEARNED enforcement

- **Symptom:** LEARNED.md existed but was never read before coding. Same bugs repeated
  across sessions. 4 known bugs in LEARNED appeared again during audit despite being recorded.
- **Root cause:** RECALL was passive — session-start.sh wrote LEARNED entries to
  .claude/CLAUDE.md but nothing BANNED coding without checking them.
- **Fix:**
  - `hooks/active-recall.py`: PreToolUse Python script that extracts keywords from
    file path, searches LEARNED.md for relevant bugs, outputs warnings to stderr.
  - `hooks/pretool-backup.sh`: Added Phase 0 → calls active-recall.py BEFORE every
    file write. Warnings shown in Claude Code transcript before code is written.
  - `.pre-commit/auto-decision.py`: Auto-records tech choices from commit messages
    → user_decisions.json. No user action needed. Debounced 10min per (type, area).
  - `.pre-commit/test-quality.py`: Records quality signals after each pytest run
    → .quality_history.json. Signals: pytest pass=+1, test files written=+1,
    fix+pass=+2. Rolling score shows quality trend.
  - `engine/dream_engine.py`: Added `_rule_based_distill()` — AI-free fallback
    for Dream Cycle when ANTHROPIC_API_KEY unavailable. Uses regex heuristics
    to extract error/decision/pattern signals. Cookbooks still written.
- **Tags:** `#hook` `#memory` `#automation` `#learned` `#workflow`
- **Lesson:** Passive RECALL doesn't work. Active enforcement via PreToolUse
  + pre-commit is required to change developer behavior.
