# LEARNED.md — Bug Fixes & Pattern Database

> Every bug fix is a permanent asset. Every mistake is a lesson learned.
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

 — every session exit 1

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

 — bleed into sibling projects

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

*Last updated: 2026-04-05*
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

