# WORKFLOW MEMORY — Knowledge That Never Gets Lost

> ∫f(t)dt — Functional Credibility Over Institutional Inertia
> Every session builds on the last. No knowledge is ever truly forgotten.

---

## The 3 Memory Layers

```
┌─────────────────────────────────────────────────────────────┐
│  LAYER 1: SESSION START (automatic, every new session)      │
│  Claude CLI opens → SessionStart hook runs                  │
│  → Shows: LEARNED.md (recent bugs) + cookbook (distilled)  │
│  → AI reads → knows what was fixed, what to avoid          │
├─────────────────────────────────────────────────────────────┤
│  LAYER 2: LEARNED.md (structured bug-fix database)          │
│  memory/LEARNED.md                                          │
│  Format: date | symptom | root cause | fix | tags          │
│  Every bug fix → add entry → permanent institutional memory │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: COOKBOOKS + DISCOVERIES (distilled knowledge)     │
│  memory/cookbooks/*.md   — Dream Cycle distills logs        │
│  memory/discoveries/     — Past project contexts            │
│  Searchable, tagged, auto-archived                         │
└─────────────────────────────────────────────────────────────┘
```

---

## Daily Workflow

### Opening a new session

```
1. claude
2. SessionStart hook runs automatically:
   - Shows LEARNED.md (recent bugs)
   - Shows most recent cookbook
   - Shows last checkpoint
   - Runs GC (silent)
3. AI automatically reads → knows past mistakes
4. You start working
```

### When you encounter an error

```
1. See error in terminal
2. BEFORE fixing → search LEARNED.md:
   grep -i "boundary\|observer\|gc" memory/LEARNED.md
3. If found → read the fix, apply it
4. If not found → fix it, then record it (see below)
```

### When you fix a bug

```
1. Identify the root cause
2. Fix the code
3. Run: pytest
4. Record in LEARNED.md (template below)
5. Commit with message: "fix: add LEARNED.md entry for <bug>"
```

---

## LEARNED.md Entry Template

Copy and fill this template for every bug fix:

```markdown
## [YYYY-MM-DD] Bug: <short description>

- **Symptom:** <what went wrong, how it manifested>
- **Root cause:** <the actual cause (not the symptom)>
- **Fix:** <exact fix applied> (`file:line`)
- **Tags:** #boundary #observer #gc #hook #threading #mcp
- **Lesson:** <one-sentence takeaway>
```

### Tags to use

| Tag | When to use |
|-----|-------------|
| `#boundary` | Path/directory scope issues |
| `#observer` | SilentObserver, watchdog, file watching |
| `#gc` | Garbage collection, cleanup |
| `#hook` | Claude Code hooks, settings.json |
| `#threading` | Concurrency, race conditions |
| `#schema` | JSON validation, config format |
| `#mcp` | MCP server, tools, resources |
| `#security` | Auth, permissions |
| `#performance` | Speed, memory, optimization |
| `#ui` | Frontend, rendering, user experience |
| `#api` | API design, endpoints, contracts |

---

## Search Commands

```bash
# Find bug by tag
grep -i "#boundary" memory/LEARNED.md
grep -i "#observer" memory/LEARNED.md

# Find by date range
grep -A 5 "## \[2026-04" memory/LEARNED.md

# Find by symptom keyword
grep -i "settings.*error\|invalid.*key" memory/LEARNED.md

# Find by root cause type
grep -i "race\|singleton\|global" memory/LEARNED.md

# Show all tags used
grep -oP '#\w+' memory/LEARNED.md | sort | uniq -c | sort -rn
```

---

## Cookbook System (Dream Cycle)

```
Every session creates logs → Dream Cycle distills them into cookbooks

Trigger: neutron dream
Or: SilentObserver (auto-triggers after 30min of silence)

Output:
  memory/cookbooks/YYYY-MM-DD_cookbook.md
  - Key events extracted
  - Patterns identified
  - Shipped/delivered summaries

Latest cookbook is shown on session start.
```

---

## Session Log System

```
Every session writes to: memory/YYYY-MM-DD.md
Checkpoint: neutron checkpoint "task description"
Handoff: neutron checkpoint --handoff (for session transfer)

Session log contains:
  - Timestamps for every action
  - Skill invocations
  - CI deltas
  - Decisions made
  - Errors encountered
```

---

## The Complete Memory Loop

```
┌──────────────────────────────────────────────────────────────┐
│                     SESSION N                                │
│                                                              │
│  OPEN SESSION                                                │
│  ├── SessionStart hook runs                                  │
│  │   ├── GC (silent cleanup)                                │
│  │   ├── Show LEARNED.md (recent bugs)     ← Layer 1       │
│  │   ├── Show cookbook (distilled knowledge) ← Layer 1       │
│  │   └── Show last checkpoint                               │
│  ├── AI reads LEARNED.md + cookbook                         │
│  └── AI knows: past bugs, patterns, shipped projects        │
│                                                              │
│  WORKING                                                     │
│  ├── Encounter error                                         │
│  │   ├── Search LEARNED.md                                  │
│  │   ├── Fix bug (if new)                                   │
│  │   └── Record in LEARNED.md (if new)     ← Layer 2       │
│  ├── Complete task → neutron ship                           │
│  └── Every action → logged to memory/YYYY-MM-DD.md          │
│                                                              │
│  END SESSION                                                 │
│  ├── neutron checkpoint --handoff                           │
│  └── Daily log auto-archived to memory/archived/             │
│                                                              │
│  LATER (Dream Cycle)                                        │
│  ├── Logs distilled → cookbooks/           ← Layer 3       │
│  ├── Discoveries archived → discoveries/   ← Layer 3       │
│  └── Old logs pruned → clean memory                        │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## File Reference

| File | Purpose | When to update |
|------|---------|----------------|
| `memory/LEARNED.md` | Bug fixes & patterns | After every bug fix |
| `memory/YYYY-MM-DD.md` | Daily session log | Every session |
| `memory/cookbooks/*.md` | Distilled knowledge | After Dream Cycle |
| `memory/discoveries/` | Project discoveries | After discovery interview |
| `memory/shipments.json` | Shipped projects | After `/ship` |
| `MEMORY.md` | Knowledge index | When system changes |

---

## Context Loading Order (For AI Reference)

When this file is loaded, read in this order:

```
1. SOUL.md              → Agent identity, forbidden actions
2. USER.md              → User preferences
3. GOVERNANCE.md        → Policy rules
4. RULES.md             → Operating procedures
5. WORKFLOW.md          → Task distribution
6. WORKFLOW_MEMORY.md   → THIS FILE — memory system workflow
7. MEMORY.md            → Long-term knowledge
8. memory/LEARNED.md   → Past bugs fixed ← ALWAYS READ THIS BEFORE FIXING
9. memory/YYYY-MM-DD.md → Today's context
```

---

## Quick Command Reference

```bash
# Before fixing anything — search past mistakes
grep -i "<keyword>" memory/LEARNED.md

# Record a new learning
# → Edit memory/LEARNED.md (follow template above)

# Trigger Dream Cycle (distill logs → cookbooks)
neutron dream

# Check system status
neutron status

# Run tests
pytest

# Search all memories
neutron memory --search "<query>"

# Export session for handoff
neutron checkpoint --handoff
```

---

## Golden Rules

> **Rule 1:** Every bug fix MUST be recorded in LEARNED.md before committing.
> **Rule 2:** Search LEARNED.md BEFORE starting any fix.
> **Rule 3:** The same mistake must never be made twice.
> **Rule 4:** If it wasn't logged, it didn't happen.
> **Rule 5:** Dream Cycle runs automatically — but can be triggered manually with `neutron dream`.

---

*Last updated: 2026-04-05*
*Part of: NEUTRON EVO OS v4.1.0*
