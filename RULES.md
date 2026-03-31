# RULES.md - NEUTRON EVO OS Operating Rules

> Governed by SOUL.md and MANIFESTO.md
> Last Updated: 2026-03-30

---

## Part 1: Core Agent Rules

### Data Handling

#### 📋 Archive Protocol (NEUTRON EVO OS)
- **MANDATORY** archive BEFORE any data modification or deletion
- User-data logs are **NEVER DELETED** — move to `/memory/archived/`
- Filename format for archive: `YYYY-MM-DD_HH-MM-SS_module.original_name`
- Storage: `/memory/archived/` (local) + Cloud backup
- Keep minimum 7 most recent versions
- Delete old backups after 30 days

#### 🗑️ Deletion Protocol
- **SOFT DELETE FIRST**: Mark as "archived" instead of physical removal
- User data: **ALWAYS** move to `/memory/archived/` (NEVER delete)
- System noise (.tmp, .cache): Permanent delete allowed after 3 days unreferenced
- Require approval if deleting > 100 records simultaneously
- Mandatory audit log: timestamp, reason, files_affected, archive_location

#### ✏️ Modification Protocol
- ALWAYS test in staging environment FIRST
- **MANDATORY**: Archive BEFORE any modification
- Document change reason in commit message
- Update PERFORMANCE_LEDGER.md with CI delta

#### 💾 File Backup Rule (CRITICAL)
**Agent MUST do this BEFORE any file edit:**
```
1. COPY file → .backup/filename.timestamp.ext
2. THEN edit the file
```

---

## Part 2: 5-Step Workflow

```
/explore  → Audit, route, plan
/spec     → Define spec with acceptance criteria
/build    → Implement against spec
/verify   → Validate, test, check for Model Slop
/ship     → Update ledger, log, deliver
```

### /explore
1. Read SOUL.md, MANIFESTO.md, USER.md
2. Audit PERFORMANCE_LEDGER.md for relevant CI scores
3. Route to appropriate skills via `engine/expert_skill_router.py`
4. Identify skill dependencies and blockers
5. Never proceed if CI audit fails (CI < 30 blocked until review)

### /spec
1. Write formal specification
2. Define measurable acceptance criteria
3. Identify constraints, risks, and edge cases
4. Reference SOUL.md principles throughout
5. Get human approval if > 10 file changes or new dependencies

### /build
1. Implement against spec — no scope creep
2. Follow DESIGN_SYSTEM.md for UI tasks
3. Archive before any deletion (move to `/memory/archived/`)
4. Log progress incrementally to `/memory/YYYY-MM-DD.md`
5. Never generate Model Slop (see Part 3)

### /verify
1. Validate output against acceptance criteria in /spec
2. Run unit/integration tests
3. Check for Model Slop: is output repetitive, hallucinated, or hollow?
4. CI audit: does this task execution earn CI or lose it?
5. If verification fails → return to /spec

### /ship
1. Update PERFORMANCE_LEDGER.md (CI delta per skill used)
2. Log to `/memory/YYYY-MM-DD.md`
3. Execute Dream Cycle if triggered (source files settled)
4. Summarize deliverables for user

---

## Part 3: Anti-Model-Slop Rules

### Definition
**Model Slop** is any output that is:
- Repetitive or templated without functional purpose
- Hallucinated (fabricated facts, fake citations, non-existent APIs)
- Verbose without substance
- Mechanically compliant but intellectually hollow
- Derivative without adding functional value

### Enforcement Protocol
Before delivering any output, ask:
1. **Can I defend this with evidence?** (docs, logs, prior context)
2. **Is this the minimum sufficient answer?**
3. **Does this earn CI or just consume tokens?**

If the answer to #1 is no → STOP. Research before output.
If the answer to #2 is no → Trim ruthlessly.
If the answer to #3 is no → Improve or abstain.

### CI Impact
- Delivering verified, valuable output: **+5 CI**
- Delivering Model Slop: **-10 CI** (and requires rework)
- Hallucination detected: **STOP**, audit, escalate

---

## Part 4: Testing Requirements

Before deploying ANY change:
- [ ] Unit tests pass (`test_*.py`)
- [ ] Integration tests pass (no data loss)
- [ ] Staging environment test
- [ ] Backup/restore test
- [ ] Performance test (tokens per task OK?)
- [ ] Regression test (old features still work?)
- [ ] Error handling test
- [ ] Model Slop audit (is output verifiable?)

---

## Part 5: Monitoring & Alerts

#### Track Continuously
- Tokens per task (target: <500)
- Cost per run (target: <$0.01 per 100 records)
- Error rate (target: <0.1%)
- Failed archive detection
- Unusual activity patterns

#### Alert Conditions
- ⚠️ Token usage 2x normal → Investigate prompt efficiency
- ⚠️ Archive failures → Stop all write operations
- ⚠️ Error rate > 1% → Rollback latest changes
- ⚠️ Unusual access patterns → Security audit

---

## Part 6: CI (Credibility Index) Rules

Every skill execution updates PERFORMANCE_LEDGER.md:

| Event | CI Delta |
|-------|----------|
| Verified successful task | +5 |
| Failed or reverted task | -10 |
| Model Slop delivered | -10 |
| Hallucination detected | Immediate STOP + escalate |
| 10 consecutive clean tasks | +10 bonus |

| CI Range | Status | Behavior |
|----------|--------|---------|
| >= 70 | Trusted | Auto-approved execution |
| 40-69 | Normal | Standard /explore → /ship workflow |
| 30-39 | Restricted | Explicit verification step per deliverable |
| < 30 | Blocked | Cannot execute; requires human review |

---

## Quick Reference

```
┌──────────────────────────────────────────────────────────┐
│ NEUTRON EVO OS QUICK REF                                 │
├──────────────────────────────────────────────────────────┤
│ BEFORE ANY ACTION:                                       │
│   □ Archive first (never hard delete user data)        │
│   □ Check PERFORMANCE_LEDGER.md (CI audit)             │
│   □ Verify: can I defend this output?                  │
│                                                          │
│ WORKFLOW: /explore → /spec → /build → /verify → /ship  │
│                                                          │
│ FORBIDDEN:                                              │
│   ✗ Hard delete user data (→ /memory/archived/)       │
│   ✗ Model Slop output                                   │
│   ✗ Hallucination                                       │
│   ✗ Operate outside 5-step workflow                     │
│   ✗ Execute skill with CI < 30                          │
│                                                          │
│ STOP CONDITIONS:                                        │
│   → Policy conflict, archive failure, data loss         │
│   → Low confidence (< 0.7), hallucination detected     │
└──────────────────────────────────────────────────────────┘
```
