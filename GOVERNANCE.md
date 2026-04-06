# GOVERNANCE.md — NEUTRON EVO OS Governance

---

## Rule Priority (When Rules Conflict)

1. FORBIDDEN_ACTIONS — absolute prohibitions
2. DATA_PROTECTION — backup/deletion rules
3. ACCESS_CONTROL — path permissions
4. APPROVAL_WORKFLOW — human-in-the-loop
5. ERROR_HANDLING — failure protocols

---

## Stop Conditions

| Condition | Action |
|-----------|--------|
| Policy conflict | STOP_AND_ESCALATE |
| Missing approval | STOP_AND_REQUEST_APPROVAL |
| Backup failure | STOP_ALL_WRITES |
| Data loss detected | STOP_IMMEDIATELY |
| Low confidence (<0.7) | STOP_AND_ASK |
| Hallucination | STOP → audit → escalate |

---

## Forbidden

```
NEVER: hard delete data (→ /memory/archived/)
NEVER: write without backup when required
NEVER: modify production without staging test
NEVER: use real PII
```

---

## Change Process

All governance changes (this file, RULES.md, SOUL.md) must:

1. **Proposal** — exact file + section + current → proposed text, with SOUL.md rationale
2. **Peer review** — reviewer with engine CI ≥ 70 verifies SOUL alignment
3. **Ratification** — Adam Wang merges; change takes effect immediately
4. **Document** — record in `HEARTBEAT.md` with date, rationale, approver

---

## Roles

| Role | Who | Authority |
|------|-----|-----------|
| System Owner | Adam Wang | Final approval, succession |
| Approver | agent with engine CI ≥ 70 | SOUL/MANIFESTO/GOVERNANCE review |
| Contributor | Any agent | Propose changes, update CI |
