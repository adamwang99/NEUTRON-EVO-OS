# GOVERNANCE.md - NEUTRON EVO OS Governance Rules

> Extracted from `RULE for CODING/Multi Agents/policy.json`
> Governed by SOUL.md (∫f(t)dt philosophy) and MANIFESTO.md
> Last Updated: 2026-03-30

---

## 1. Priority Order

When rules conflict, follow this priority:
1. **FORBIDDEN_ACTIONS** - Absolute prohibitions
2. **DATA_PROTECTION_RULES** - Backup/deletion rules
3. **ACCESS_CONTROL** - Path-based permissions
4. **APPROVAL_WORKFLOW** - Human-in-the-loop
5. **ERROR_HANDLING** - Failure protocols
6. **OBSERVABILITY** - Monitoring
7. **OPTIMIZATION** - Performance rules
8. **USER_REQUEST** - User intent

---

## 2. Stop Conditions

| Condition | Action |
|-----------|--------|
| Policy conflict | STOP_AND_ESCALATE |
| Missing approval | STOP_AND_REQUEST_APPROVAL |
| Backup failure | STOP_ALL_WRITES |
| Data loss detected | STOP_IMMEDIATELY |
| Low confidence (<0.7) | STOP_AND_ASK |

---

## 3. Forbidden Actions

```
NEVER DO:
- HARD_DELETE_ANY_DATA
- DELETE_WITHOUT_EXPLICIT_CONFIRMATION
- MODIFY_PRODUCTION_WITHOUT_STAGING_TEST
- WRITE_WITHOUT_BACKUP_WHEN_REQUIRED
- USE_REAL_PII
- CHANGE_SYSTEM_PROMPT_MID_SESSION
```

---

## 4. Access Control by Path

### `/data/production`
- ✅ READ, MODIFY_WITH_APPROVAL, BACKUP
- ❌ DELETE, RECREATE
- ⚠️ Approval required (min 1 approver)
- ⚠️ Backup before action required
- ⚠️ Notify team

### `/data/staging`
- ✅ READ, WRITE, DELETE, MODIFY
- ⚠️ Backup before delete
- ⚠️ Soft delete first

### `/logs`
- ✅ READ, APPEND
- ❌ DELETE, MODIFY

### `/backups`
- ✅ READ, CREATE_BACKUP, LIST
- ❌ DELETE
- ⚠️ Auto cleanup after 30 days

---

## 5. Data Protection Rules

### Backup Strategy
| Trigger | Action |
|---------|--------|
| BEFORE_MODIFY | Auto backup |
| BEFORE_DELETE | Auto backup |
| BEFORE_CODE_DEPLOY | Auto backup |
| DAILY_MIDNIGHT | Daily backup |
| WEEKLY_SUNDAY | Weekly backup |

### Retention Policy
- Recent backups: Keep 30
- Daily backups: 7 days
- Weekly backups: 3 months
- Monthly backups: 1 year
- Cleanup: Daily

### Deletion Rules
- **NEVER hard delete** → Always soft delete first
- **Soft delete wait**: 7 days before permanent
- **Approval threshold**: > 100 records = 1 approver
- **Audit logging**: Mandatory (timestamp, user_id, reason, records_affected)

---

## 6. Error Handling

### Critical Operations
```
DELETE, MODIFY_PRODUCTION, DEPLOY
```

### Critical Operation Policy
- Auto recovery: DISABLED
- Human approval: REQUIRED
- Error logging: FULL_CONTEXT
- Notify immediately: YES
- Preserve state for debugging: YES

### Common Errors Response
| Error | Action |
|-------|--------|
| API_TIMEOUT | Retry 3x (exponential backoff), then alert |
| VALIDATION_FAILED | Log 5 samples, manual review |
| DATA_LOSS_DETECTED | STOP immediately, restore backup, notify team |

---

## 7. Observability

### Metrics to Monitor
- tokens_per_task (target: <500)
- cost_per_run (target: <$0.01 per 100 records)
- error_rate (target: <0.1%)
- backup_success_rate
- data_integrity_checks

### Alert Thresholds
| Condition | Threshold |
|-----------|-----------|
| Token usage | 2x normal |
| Error rate | >1% |
| Backup failure | IMMEDIATE |
| Delete spike | 3x normal |

---

## 8. Optimization Rules

### Prompt Caching
- Enabled: YES
- TTL: 3600 seconds (1 hour)
- Avoid system prompt changes mid-session

### Batch Processing
- Enabled: YES
- Min batch size: 5
- Max batch size: 100
- Timeout: 300 seconds

### Context Optimization
- Use RAG when possible
- Context length limit: 2000 tokens
- Include only relevant data
- Summarize long context

---

## 9. Change Process

All governance changes (GOVERNANCE.md, RULES.md, CONTRIBUTING.md, this file)
must follow this 4-step process:

### Step 1 — Proposal
Write a pull request or GitHub issue with:
- **What** is changing (exact file + section + current text → proposed text)
- **Why** it is changing (justification, evidence of a real problem)

### Step 2 — Justification Required
Every change must cite:
- Which SOUL.md or MANIFESTO.md principle it serves
- Evidence: bug, inconsistency, missing coverage, or new requirement
- Why preserving the status quo is worse risk

### Step 3 — Peer Review
- **Files SOUL.md, MANIFESTO.md, GOVERNANCE.md**: Review required from any agent
  with CI ≥ 70 on the `engine` skill
- **Files RULES.md, PERFORMANCE_LEDGER.md**: Any trusted agent (CI ≥ 40)
- Reviewer verifies: SOUL alignment, no CI manipulation, no authority creep
- Reviewer approves or requests changes in writing

### Step 4 — Ratification
- After approval: Adam Wang (system owner) merges
- Change takes effect immediately on merge
- Document the decision in `HEARTBEAT.md` with date, rationale, and approver
- Governance changes retroactively applied to past violations are **invalid**

### Emergency Override
In a genuine incident (data loss, security breach, system failure), any agent
may enact immediate changes without full review, but must:
1. Document the change and rationale in `memory/YYYY-MM-DD.md` within 1 hour
2. Notify Adam Wang within 1 hour
3. Submit a full proposal within 24 hours for post-hoc ratification

---

## 10. Roles

| Role | Who | Authority |
|------|-----|-----------|
| **System Owner** | Adam Wang | Final approval on all governance changes, succession decisions |
| **Approver** | Any agent with engine CI ≥ 70 | Peer review sign-off on SOUL/MANIFESTO/GOVERNANCE changes |
| **Contributor** | Any agent | Propose changes, update CI, add skills per CONTRIBUTING.md |
| **Reviewer** | Any trusted agent (CI ≥ 40) | Peer review on RULES.md and PERFORMANCE_LEDGER.md |

### Succession
If Adam Wang is unavailable for > 30 days:
1. System continues operating under current governance
2. Any trusted agent (CI ≥ 70, engine skill) may act as interim Approver
3. Governance changes require consensus of 2 approvers + Adam Wang ratification on return
4. No fundamental changes (SOUL.md, MANIFESTO.md) until succession resolved

---

## Quick Reference Card

```
┌─────────────────────────────────────────────────────────┐
│ BEFORE ANY ACTION:                                      │
│ 1. Is it forbidden? → STOP                              │
│ 2. Do I have access? → Check path rules                │
│ 3. Do I need backup? → Create first                    │
│ 4. Do I need approval? → Get it                        │
│ 5. Is it critical? → Alert human                       │
└─────────────────────────────────────────────────────────┘
```
