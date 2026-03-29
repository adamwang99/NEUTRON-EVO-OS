# GOVERNANCE.md - NEUTRON EVO OS Governance Rules

> Governed by SOUL.md (∫f(t)dt philosophy) and MANIFESTO.md
> Last Updated: 2026-03-30

## Priority Order
1. FORBIDDEN_ACTIONS — Absolute prohibitions
2. DATA_PROTECTION_RULES — Archive/deletion rules
3. ACCESS_CONTROL — Path-based permissions
4. APPROVAL_WORKFLOW — Human-in-the-loop
5. ERROR_HANDLING — Failure protocols

## Stop Conditions
| Condition | Action |
|-----------|--------|
| Policy conflict | STOP_AND_ESCALATE |
| Missing approval | STOP_AND_REQUEST_APPROVAL |
| Archive failure | STOP_ALL_WRITES |
| Data loss detected | STOP_IMMEDIATELY |
| Low confidence (<0.7) | STOP_AND_ASK |

## Forbidden Actions
- HARD_DELETE_ANY_DATA
- DELETE_WITHOUT_EXPLICIT_CONFIRMATION
- MODIFY_PRODUCTION_WITHOUT_STAGING_TEST
- WRITE_WITHOUT_BACKUP_WHEN_REQUIRED
- USE_REAL_PII
- GENERATE_MODEL_SLOP

## Archive Strategy (NEUTRON EVO OS)
| Trigger | Action |
|---------|--------|
| BEFORE_DELETE | Archive to /memory/archived/ |
| DREAM_CYCLE | Auto-archive old logs |
| USER_DATA | Move, never delete |

## CI (Credibility Index)
- Skills earn CI through verified task completion
- CI < 40: restricted use
- CI >= 70: full trust
