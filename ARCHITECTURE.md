# ARCHITECTURE.md — NEUTRON EVO OS System Architecture

> How the components fit together: context loading → skill routing → execution →
> checkpointing → memory.
> Maintained by: Adam Wang | Last Updated: 2026-03-31

---

## System Overview

NEUTRON EVO OS is a **plugin/integration layer** for AI coding agents. It is not
a desktop application. It provides:

- Persistent context (who I am, what the rules are)
- Skill routing (which subsystem handles this task)
- Memory management (what happened in past sessions)
- Checkpointing (where did we leave off)
- CLI tooling (MemoryOS, checkpoint CLI)

Target integrations: **Claude Code**, **Cursor**, **VS Code** (extension),
**any CLI tool** that reads markdown context files.

---

## Component Map

```
┌─────────────────────────────────────────────────────────┐
│                    USER / HUMAN                          │
│            (Adam Wang, project owner)                    │
└────────────────────┬────────────────────────────────────┘
                     │ user request
                     ▼
┌─────────────────────────────────────────────────────────┐
│               AI AGENT (Claude Code, Cursor, etc.)       │
│                                                          │
│  Session starts → reads context files (see §Data Flow) │
│  Task arrives   → routes to skill via expert_skill_router│
│  Work settles   → SilentObserver triggers Dream Cycle  │
└────┬──────────────────┬───────────────────┬────────────┘
     │                  │                   │
     ▼                  ▼                   ▼
┌─────────┐    ┌──────────────┐   ┌─────────────────┐
│ ENGINE  │    │ SKILLS/      │   │ MEMORY/         │
│         │    │ core/         │   │ YYYY-MM-DD.md   │
│ • skill │    │ context/     │   │ archived/       │
│   router│    │ SKILL.md     │   │ cookbooks/       │
│         │    │ memory/      │   │ learned/        │
│ • dream │    │ SKILL.md     │   └─────────────────┘
│   engine│    │ workflow/    │             ▲
│         │    │ SKILL.md     │             │ write
│ • smart │    │ checkpoint/  │             │
│   observer│  │ SKILL.md     │   ┌─────────────────┐
│         │    └──────────────┘   │  MemoryOS CLI   │
│ • check-│                        │  (Node.js)      │
│   point │                        │  src/commands/  │
│   _cli  │                        └─────────────────┘
└─────────┘

┌─────────────────────────────────────────────────────────┐
│         INSTALLATION LAYER (install-global.sh)          │
│                                                          │
│  ~/.claude/settings.json  → NEUTRON hooks (SessionStart, │
│                             PreToolUse)                   │
│  ~/.claude/CLAUDE.md      → Global fallback context     │
│  ~/.neutron-evo-os/       → Full repo (symlink or clone) │
│  $PROJECTS_DIR/<proj>/   → Per-project NEUTRON files    │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│              VS CODE EXTENSION LAYER                     │
│                                                          │
│  vscode-extension/extension.ts  → VS Code extension      │
│  vscode-extension/templates/   → CLAUDE.md, SOUL.md,     │
│                                  etc. (install into new    │
│                                  projects)                │
└─────────────────────────────────────────────────────────┘
```

---

## Core Engine Components

### `engine/expert_skill_router.py`
**Role:** Task routing + CI management

```
User task string
       │
       ▼
keyword matching against SKILL_KEYWORDS
       │
       ├─► matched skill → execute SKILL.md logic
       │
       └─► no match → return "context" as default

After execution → update_ci(delta) under filelock
```

- **Language:** Python 3.8+
- **State:** `PERFORMANCE_LEDGER.md` (atomic writes via `filelock`)
- **No DB:** All state is human-readable Markdown

### `engine/dream_engine.py`
**Role:** Memory 2.0 — archive → prune → distill

```
Phase 1 Archive:  copy memory/YYYY-MM-DD.md → memory/archived/
Phase 2 Prune:    delete .tmp/.cache older than 3 days
Phase 3 Distill:  compress patterns → memory/cookbooks/*.md
       │
       ▼
Schedule next Dream Cycle (every 7 days, or on SilentObserver trigger)
```

- **Trigger:** SilentObserver (file-system settled for 30s) OR manual `make dream`
- **Concurrency:** `threading.Event()` re-entrancy guard — only one cycle at a time
- **Import:** Does NOT import `dream_engine` at top-level from other engine modules

### `engine/smart_observer.py`
**Role:** File-system watchdog with debounce

```
watchdog.Observer monitors a directory tree
       │
       ▼ (30s debounce — work must "settle")
File change detected
       │
       ▼ (debounce elapsed, no new changes)
callback() → dream_cycle()
```

- **Concurrency:** `threading.Lock` protects singleton state (`_running`, `_thread`)
- **Lifecycle:** `start()` / `stop()` class methods
- **Daemon:** Observer thread is daemon — exits with main process

### `engine/checkpoint_cli.py`
**Role:** Session checkpointing — save/restore work-in-progress

```
--write --task "..." --notes "..." --confidence [low|medium|high]
       │
       ▼
Prepend checkpoint entry to memory/YYYY-MM-DD.md
Format: ## [HH:MM] — Task: ...\n- Action: ...\n- Outcome: ...

--read  → print latest checkpoint
--handoff → write full session transcript + checkpoint
```

---

## Skill Architecture

### Skill Structure
```
skills/core/<name>/
├── SKILL.md               # Metadata + execution logic (REQUIRED)
├── logic/__init__.py      # Phase 5: actual implementation stubs
└── validation/__init__.py # Phase 5: validation stubs
```

### Core Skills

| Skill | Role | CI | Key File |
|-------|------|----|----|
| `context` | Context loading, injection, priority | 60 | `skills/core/context/SKILL.md` |
| `memory` | Daily logs, archive, MemoryOS | 55 | `skills/core/memory/SKILL.md` |
| `workflow` | 5-step execution, parallel dispatch | 50 | `skills/core/workflow/SKILL.md` |
| `engine` | Skill router, dream, observer | 80 | `engine/*.py` |
| `checkpoint` | Checkpoint CLI, handoff | 60 | `engine/checkpoint_cli.py` |

### Skill CI Lifecycle
```
New skill registered → CI = 50
     │
     ├── Success → +5 CI per task
     ├── Clean 5-step workflow → +15 CI
     ├── Failure → -10 CI
     ├── Archive failure → -20 CI + STOP
     └── Hallucination → STOP + escalate
```

---

## Memory Architecture

```
memory/
├── YYYY-MM-DD.md          ← Daily session log (append-only)
├── archived/              ← Archived logs and user data (NEVER DELETE)
│   └── YYYY-MM-DD_HH-MM-SS_*.md
├── cookbooks/             ← Distilled knowledge summaries (Dream Cycle)
│   └── *.md               ← Topic compressions
└── learned/               ← Learned skill patterns (Phase 5)
```

### Daily Log Entry Format
```markdown
## [HH:MM] — Task: <brief description>
- Action: <what was done>
- Outcome: <result>
- CI delta: <+/-N>
- Notes: <anything worth remembering>
```

### Archive Protocol
- **User data:** ALWAYS move to `memory/archived/` before deletion
- **Naming:** `YYYY-MM-DD_HH-MM-SS_original-name.ext`
- **Retention:** Archived data is **never hard-deleted**

---

## Data Flow: Session Lifecycle

```
1. SESSION START
   Claude Code starts
         │
         ▼
   ~/.claude/CLAUDE.md read (global fallback)
         │
         ▼
   ~/.claude/settings.json → SessionStart hook fires
         │
         ▼
   NEUTRON_ROOT context files loaded in priority order:
     P0: SOUL.md, MANIFESTO.md
     P1: USER.md, GOVERNANCE.md, RULES.md
     P2: PERFORMANCE_LEDGER.md
     P3: memory/YYYY-MM-DD.md (today's log)
         │
         ▼
   MemoryOS "wake": session context recovered from previous checkpoint
         │
         ▼
   Agent ready.

2. TASK EXECUTION
   User delivers task
         │
         ▼
   expert_skill_router.route_task(task_string)
         │
         ▼
   Skill selected → execution per SKILL.md
         │
         ▼
   After execution: update_ci(delta) → PERFORMANCE_LEDGER.md

3. WORK SETTLES (SilentObserver)
   30s debounce passes with no new file changes
         │
         ▼
   dream_engine.dream_cycle() triggered
   (Archive → Prune → Distill)
         │
         ▼
   Dream Cycle logged, last_dream updated in SKILL.md

4. SESSION END
   memoryos sleep "summary" --next "next task"
         │
         ▼
   Writes:
     - memory/transcript.md      (full session log)
     - memory/handoff.md         (context for next session)
     - engine/checkpoint_cli --write (checkpoint entry)
         │
         ▼
   Session complete.
```

---

## Phase Roadmap

| Phase | Description | Status |
|-------|-------------|--------|
| 1–4 | Emergency patches, stabilization, integration, docs | ✅ **COMPLETE** |
| 5 | Skill logic/validation modules, Phase 5 plugin system | ✅ **COMPLETE** |
| 6 | MCP server (Model Context Protocol) | ✅ **COMPLETE** |
| 7 | Cursor/Cline integration layer | 🔲 Planned |
| 8 | Learned skills pipeline (skills/learned/) | 🔲 Planned |

---

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| No database | Markdown files are human-readable, git-versionable, mergeable |
| CI stored in Markdown | No separate system needed; visible to all agents |
| Skills as directories | Self-contained, independently versionable, CI-tracked |
| Dream Cycle on file settle | Reduces noise; only runs when work has actually paused |
| Atomic ledger writes (filelock) | Concurrent agents would corrupt non-locked file |
| Symlink `~/.neutron-evo-os` | Source of truth is one directory; projects reference it |
| CLI over GUI | Agent-native interface; no rendering overhead |

---

## File Locations

| File/Dir | Location |
|----------|----------|
| NEUTRON_ROOT | `$HOME/.neutron-evo-os` (or `ai-context-master/` during dev) |
| Global settings | `~/.claude/settings.json` |
| Global fallback | `~/.claude/CLAUDE.md` |
| Daily memory | `$NEUTRON_ROOT/memory/YYYY-MM-DD.md` |
| Skill registry | `$NEUTRON_ROOT/skills/core/*/SKILL.md` |
| Engine modules | `$NEUTRON_ROOT/engine/*.py` |
| MemoryOS CLI | `$NEUTRON_ROOT/MemoryOS/src/index.js` |
| VS Code extension | `$NEUTRON_ROOT/vscode-extension/extension.ts` |
| VS Code templates | `$NEUTRON_ROOT/vscode-extension/templates/` |
| Backup files | `$NEUTRON_ROOT/.backup/` |

---

*This document is the authoritative system architecture reference. When in doubt,
trace the data flow above. If a component is missing from this diagram, add it.*
