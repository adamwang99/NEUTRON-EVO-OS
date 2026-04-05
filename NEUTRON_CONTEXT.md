# NEUTRON EVO OS — Global Context

## 🚨 MANDATORY FIRST STEP

**BEFORE doing ANYTHING else (before greeting, before asking questions):**

```
1. Read /home/adam/.neutron-evo-os/memory/.auto_confirm.json
2. IF {"enabled": true}:
   - discovery=true  → SKIP ALL interview questions
                        → Write DISCOVERY.md using user's prompt directly
                        → Go to /spec
   - spec=true       → After writing SPEC.md → do NOT show USER REVIEW gate
                        → AUTO-APPROVE, go to /build
   - acceptance=true → After /build → do NOT show USER TEST gate
                        → AUTO-PASS, go to /ship
   - ALWAYS: only /ship rating is requested from user
3. IF {"enabled": false} OR file not found → normal flow
```

**🚫 FORBIDDEN — ABSOLUTE RULES, NO EXCEPTIONS:**
- ❌ Never ask ANY discovery question when `discovery=true` is active
- ❌ Never show SPEC USER REVIEW gate when `spec=true` is active
- ❌ Never show ACCEPTANCE TEST gate when `acceptance=true` is active
- ❌ Never say "is this correct?" or "do you approve?" when gates are bypassed
- ✅ ONLY the /ship rating is always requested, even in auto-confirm mode

## 🧠 Memory Retrieval (How AI Knows What Was Learned)

Every new session automatically sees via SessionStart hook:
1. `memory/LEARNED.md` — bug fixes & patterns from past sessions
2. `memory/cookbooks/*.md` — distilled knowledge from Dream Cycle (most recent shown)
3. `memory/discoveries/` — past project discoveries
4. `memory/YYYY-MM-DD.md` — today's session log
5. Full reference: `WORKFLOW_MEMORY.md` (memory system workflow)

## 🗄️ 3-Tier Memory System (AI Gatekeeper)

Every tier has an AI (Claude Opus) acting as gatekeeper — deciding what matters.

| Tier | Storage | AI Gatekeeper Role | Retention |
|------|---------|--------------------|-----------|
| SHORT: Active log | `memory/YYYY-MM-DD.md` | Pre-filter noise (skill checkpoints, test passes, read-only) before AI analysis | Live, truncated if >10k lines |
| MID: Cookbooks | `memory/cookbooks/*.md` | AI synthesizes → Decision Tree format: trigger/recognition/resolution/prevention | Never (overwritten by distill) |
| LONG: LEARNED.md | `memory/LEARNED.md` | AI suggests → human approves → permanent entry | Never |
| LONG: LEARNED_pending | `memory/pending/LEARNED_pending.md` | AI drafts awaiting human approval | 7-day auto-archive |
| LONG: Archived | `memory/archived/` | Raw logs compressed by Dream Cycle | 7 days |

**Dream Cycle trigger:** `neutron dream` (manual) or auto after 30min silence.

**Noise pre-filter (before AI sees logs):**
- Skill checkpoints (`Skill: X | Task: Y`) — repeated format
- Test passes, read-only commands (grep, ls, cat, pwd, find)
- Duplicate events (≥3x identical normalized line)
- Generic `execution_error` without stack trace

**AI analysis output:** Decision Tree cookbooks with trigger → recognition → resolution → prevention.

**Search past bugs:**
```bash
grep -i "boundary\|observer\|gc\|hook" memory/LEARNED.md
```

**Pending LEARNED approvals:**
```bash
neutron memory pending              # list pending entries
neutron memory approve <draft_id>  # approve → LEARNED.md
neutron memory reject <draft_id>   # reject → archived
```

Disk space via `neutron gc`. GC runs automatically every session start (silent).
Manual cleanup:

```bash
neutron gc                              # dry-run: preview
neutron gc --pycache --tests --data-json  # full cleanup
neutron gc --large 50                  # delete files > 50MB
```

## 🌐 Multi-Window Hub/Satellite Architecture

When running multiple Claude Code windows (each in a different project), knowledge is shared via the **hub**:

```
~/.neutron-evo-os/         ← HUB (ai-context-master/ — central knowledge)
├── memory/LEARNED.md       ← Accumulated bugs from ALL projects
├── memory/decisions.json   ← Accumulated decisions from ALL projects
└── memory/index.json       ← Registry: project → last sync time

/mnt/data/projects/octa/   ← SATELLITE
└── memory/YYYY-MM-DD.md   ← Local session log (project-specific)

/mnt/data/projects/bot/    ← SATELLITE
└── memory/YYYY-MM-DD.md   ← Local session log (project-specific)
```

**Knowledge flow:**
1. Session ends in satellite project → `neutron memory sync` extracts **structured** LEARNED entries from local LEARNED.md (NOT raw log excerpts)
2. Structured entries merged into hub `LEARNED.md` + `decisions.json` (deduplicated)
3. Next session (any project) → `session-start.sh` reads hub LEARNED.md + pending → sees accumulated learnings from all projects
4. Pending entries (AI suggestions) shown at session start → user approves/rejects

**Sync command:**
```bash
neutron memory sync                # push local learnings to hub
neutron memory sync --hub /path    # override hub path
```

**NEUTRON_HUB** env var (set by launcher) = path to hub engine. **NEUTRON_ROOT** = current project.

## ⚡ Quick Reference

| Task | Command |
|------|---------|
| Auto-confirm ON | `neutron auto full` |
| Auto-confirm OFF | `neutron auto disable` |
| System status | `neutron status` |
| Version info | `neutron version` |
| Garbage collection | `neutron gc --pycache --tests --data-json` |
| Backup before upgrade | `neutron protect --dry-run` |
| Run Dream Cycle | `neutron dream` |
