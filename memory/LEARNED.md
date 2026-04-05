# LEARNED.md — Bug Fixes & Pattern Database

> Every bug fix is a permanent asset. Every mistake is a lesson learned.
> ∫f(t)dt — Functional Credibility Over Institutional Inertia

---

## [2026-04-05] Bug: Observer scan parent directory — bleed into sibling projects

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
