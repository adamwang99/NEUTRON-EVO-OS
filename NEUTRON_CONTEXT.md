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

## 🗄️ 3-Tier Memory System

| Tier | Storage | When Auto-Pruned | Retention |
|------|---------|------------------|-----------|
| SHORT: Active log | `memory/YYYY-MM-DD.md` | Truncated to 500 lines if >10k lines | Live, never deleted |
| MID: Cookbooks | `memory/cookbooks/*.md` | Never | Until overwritten by next distill |
| LONG: Archived | `memory/archived/` | 7 days | Auto-deleted oldest |
| LONG: LEARNED.md | `memory/LEARNED.md` | Never | Permanent institutional memory |
| LONG: Discoveries | `memory/discoveries/` | Never | Permanent |

**Dream Cycle trigger:** `neutron dream` or auto after 30min silence.

**Search past bugs:**
```bash
grep -i "boundary\|observer\|gc\|hook" memory/LEARNED.md
```

Disk space is protected via `neutron gc`. GC runs automatically every session start (silent).
Manual full cleanup when needed:

```bash
neutron gc                              # dry-run: preview what would be deleted
neutron gc --data-json                  # delete test/agent dump files
neutron gc --pycache                    # delete __pycache__ and *.pyc
neutron gc --tests                     # delete pytest cache
neutron gc --pycache --tests --data-json  # full cleanup (most common)
neutron gc --retention 3               # archived/ retention: 3 days
neutron gc --large 50                  # delete files > 50MB outside git
neutron gc --empty                     # remove empty directories
```

GC runs automatically on every Claude Code session start (silent, no output).
Use `neutron gc --dry-run` to preview before running.

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
