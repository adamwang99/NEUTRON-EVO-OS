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
│  Format: date | symptom | root cause | fix | tags           │
│  Every bug fix → add entry → permanent institutional memory  │
├─────────────────────────────────────────────────────────────┤
│  LAYER 3: COOKBOOKS + DISCOVERIES (distilled knowledge)     │
│  memory/cookbooks/*.md   — Dream Cycle distills logs         │
│  memory/discoveries/     — Past project contexts             │
│  memory/shipments.json   — Shipped projects + ratings       │
│  memory/decisions.json   — Key decisions made               │
└─────────────────────────────────────────────────────────────┘
```

---

## RULES — Absolute Rules, No Exceptions

### RULES 1: Backup Before Any Change

> NEVER edit or write a file without backup.

```
When: Before Edit or Write tool runs
How:  PreToolUse hook runs automatically
      → backs up to $NEUTRON_ROOT/.backup/{project}_{date}/
      → never skip, never disable

What is backed up:
  - Every file before Edit/Write
  - Timestamped: filename.YYYYMMDD_HHMMSS.bak
  - Organized by project and date

What NOT to back up:
  - node_modules/, __pycache__/, .git/
  - *.pyc, *.tmp, *.cache
  - Files in .gitignore
```

### RULES 2: Test Before Commit

> NEVER commit if tests fail.

```
Step-by-step:
  1. Make changes
  2. python3 -m pytest        ← MUST PASS (70/70 minimum)
  3. If tests fail → fix first, then retry
  4. git add <specific files>  ← NOT git add -A
  5. git commit -m "..."
  6. NEVER skip hooks (--no-verify)
  7. NEVER skip gpg-sign (--no-gpg-sign)
```

### RULES 3: Change Logging — Every Change Must Be Logged

> If it wasn't logged, it didn't happen.

Every meaningful change requires an entry in the appropriate log:

#### 3a. For bug fixes → LEARNED.md
```
After fixing any bug:
  1. Identify: symptom, root cause, exact fix (file:line)
  2. Add entry to memory/LEARNED.md (template below)
  3. Tag it: #boundary, #observer, #gc, #hook, etc.
  4. Commit message: "fix: add LEARNED.md entry for <bug>"
```

#### 3b. For decisions → memory/user_decisions.json
```
When: A decision is made (tech choice, approval, rejection)
Format:
  {
    "id": N,
    "timestamp": "...",
    "decision": "...",
    "context": "...",
    "outcome": "pending|applied|rejected"
  }
Example:
  - SPEC approved → record decision
  - Tech stack chosen → record decision
  - Architecture change → record decision
```

#### 3c. For shipped features → memory/shipments.json
```
When: /ship step completes
Format:
  {
    "id": N,
    "project": "...",
    "rating": 1-5,
    "steps_completed": [...]
  }
The shipment entry captures: what was built, how long, user rating
```

#### 3d. For session actions → memory/YYYY-MM-DD.md
```
When: Every session
Format: ## [HH:MM] — <action>
  - Action taken
  - Outcome (ok/error/blocked)
  - CI delta
  - Notes
Checkpoint: neutron checkpoint "task description"
```

### RULES 4: Version & Release Management

> Every release must update CHANGELOG.md and bump version.

```
Version format: Major.Minor.Patch (semver)
  - Major: breaking changes (incompatible API)
  - Minor: new features (backward compatible)
  - Patch: bug fixes (backward compatible)

When to bump:
  - PATCH (x.x.1): bug fix, security patch
  - MINOR (x.1.0): new feature, new capability
  - MAJOR (1.0.0): breaking changes

Release checklist:
  [ ] All tests pass (pytest)
  [ ] CHANGELOG.md updated (## [Version] — YYYY-MM-DD)
  [ ] Version bumped in: __init__.py, package.json
  [ ] git tag: git tag -a v1.2.3 -m "Release v1.2.3"
  [ ] git push --tags
  [ ] neutron ship (record in shipments.json)

Current version: Check NEUTRON_CONTEXT.md or __init__.py
```

### RULES 5: Commit Discipline

> Commits must be atomic, intentional, and traceable.

```
Format:
  <type>: <short description (≤72 chars)>

  [blank line]
  <body: what changed, why, impact>

  Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>

Types:
  fix:     Bug fix
  feat:    New feature
  docs:    Documentation only
  refactor: Code change (no feature/bug change)
  chore:   Maintenance (deps, config, CI)
  test:    Adding or updating tests
  perf:    Performance improvement

Rules:
  - One logical change per commit
  - Commit message must explain WHY, not just WHAT
  - NEVER commit: .env, credentials.json, *.pyc, node_modules/
  - git add <specific files> — never git add -A
  - NEVER skip hooks (--no-verify)
  - NEVER skip GPG sign (--no-gpg-sign)

Good commit message:
  fix: add directory boundary guards to prevent observer scope leaks

  Added boundary validation in observer_start() to reject parent
  directories before starting SilentObserver. This prevents the
  observer from scanning sibling projects when NEUTRON_ROOT is
  misconfigured.

  - skills/core/engine/logic/__init__.py: +boundary validation
  - engine/smart_observer.py: +_root tracking in stop()
  - engine/dream_engine.py: pass root to stop()
```

### RULES 6: Never Repeat Mistakes

> Every bug fix MUST be recorded before committing.

```
Workflow:
  1. Encounter bug
  2. Search LEARNED.md: grep -i "<keyword>" memory/LEARNED.md
  3. Found? → apply existing fix, skip to step 7
  4. Not found? → fix the bug
  5. pytest must pass
  6. Record in LEARNED.md (see template below)
  7. Commit
  8. Never make the same mistake again
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
3. AI reads LEARNED.md → knows past mistakes
4. You start working
```

### When you fix a bug (complete step-by-step)

```
1. [BEFORE] grep -i "<keyword>" memory/LEARNED.md
   → Found: apply existing fix, done
   → Not found: continue to step 2

2. [FIX] Edit the code
   → PreToolUse hook auto-backs up the file

3. [TEST] python3 -m pytest
   → FAIL: fix test first, repeat
   → PASS: continue

4. [RECORD] Add entry to memory/LEARNED.md
   (see template below)

5. [COMMIT] git add <files> && git commit -m "fix: ..."

6. [VERSION] (if release)
   → Update CHANGELOG.md
   → Bump version
   → git tag vX.Y.Z
```

---

## LEARNED.md Entry Template

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

# Find recent decisions
cat memory/user_decisions.json | python3 -m json.tool

# Find recent shipments
cat memory/shipments.json | python3 -m json.tool | grep -A 5 "rating"
```

---

## The Complete Memory Loop

```
┌──────────────────────────────────────────────────────────────┐
│                     SESSION N                                │
│                                                              │
│  OPEN SESSION                                                │
│  ├── SessionStart hook: GC, LEARNED.md, cookbook, checkpoint│
│  ├── AI reads LEARNED.md → knows past mistakes              │
│  └── AI knows: past bugs, patterns, shipped projects        │
│                                                              │
│  WORKING                                                     │
│  ├── Encounter error → grep LEARNED.md                       │
│  ├── Fix bug → pytest → record LEARNED.md → commit          │
│  │      (PreToolUse hook auto-backs up files)               │
│  ├── Make decision → record in user_decisions.json           │
│  ├── Complete task → neutron ship → shipments.json           │
│  └── Every action → logged to memory/YYYY-MM-DD.md          │
│                                                              │
│  END SESSION                                                 │
│  ├── neutron checkpoint --handoff                            │
│  └── Daily log auto-archived to memory/archived/             │
│                                                              │
│  DREAM CYCLE (auto or neutron dream)                         │
│  ├── Logs distilled → cookbooks/                             │
│  ├── Discoveries → discoveries/                             │
│  └── Old logs pruned (7-day retention)                      │
│                                                              │
│  RELEASE                                                     │
│  ├── CHANGELOG.md updated                                   │
│  ├── Version bumped (semver)                                 │
│  └── git tag vX.Y.Z → git push --tags                       │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

---

## File Reference

| File | Purpose | When to update |
|------|---------|----------------|
| `memory/LEARNED.md` | Bug fixes & patterns | After every bug fix |
| `memory/user_decisions.json` | Key decisions | After every decision |
| `memory/shipments.json` | Shipped projects + ratings | After `/ship` |
| `memory/YYYY-MM-DD.md` | Daily session log | Every session |
| `memory/cookbooks/*.md` | Distilled knowledge | After Dream Cycle |
| `memory/discoveries/` | Project discoveries | After discovery interview |
| `CHANGELOG.md` | Version history | Before every release |
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
6. WORKFLOW_MEMORY.md   → THIS FILE — memory + RULES workflow
7. MEMORY.md            → Long-term knowledge
8. memory/LEARNED.md  → Past bugs fixed ← ALWAYS READ BEFORE FIXING
9. memory/YYYY-MM-DD.md → Today's context
```

---

## Quick Command Reference

```bash
# Before fixing anything — search past mistakes
grep -i "<keyword>" memory/LEARNED.md

# Run tests (mandatory before commit)
python3 -m pytest tests/ -v

# Record a bug fix → memory/LEARNED.md

# Record a decision → memory/user_decisions.json

# Record a shipment → neutron ship (after /ship step)

# Trigger Dream Cycle (distill logs → cookbooks)
neutron dream

# System status
neutron status

# Export session for handoff
neutron checkpoint --handoff

# Version bump
git tag -a vX.Y.Z -m "Release vX.Y.Z"
git push --tags
```

---

## Golden Rules

> Rule 1: Backup before any change (PreToolUse hook is automatic — never disable it).
> Rule 2: Test before commit — pytest must pass before committing.
> Rule 3: Every bug fix MUST be recorded in LEARNED.md before committing.
> Rule 4: Every decision MUST be recorded in user_decisions.json.
> Rule 5: Every release MUST update CHANGELOG.md and bump version.
> Rule 6: Commits must be atomic, intentional, with meaningful messages.
> Rule 7: If it wasn't logged, it didn't happen.
> Rule 8: Never skip hooks or GPG sign. Never commit credentials.

---

## Version History

| Version | Date | Summary |
|---------|------|---------|
| v4.1.0 | 2026-04-05 | Memory system: LEARNED.md, cookbooks, SessionStart retrieval |

---

*Last updated: 2026-04-05*
*Part of: NEUTRON EVO OS v4.1.0*
