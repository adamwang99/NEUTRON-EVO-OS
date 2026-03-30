# NEUTRON-EVO-OS: Performance Ledger

> ∫f(t)dt — Functional Credibility Over Institutional Inertia
> Last Updated: 2026-03-30

---

## Agent / Skill Credibility Index

| Skill | CI Score | Tasks Completed | Last Active |
|-------|----------|-----------------|-------------|
| context | 55 | 1 | 2026-03-30 |
| memory | 50 | 0 | - |
| workflow | 50 | 0 | - |
| engine | 75 | 1 | 2026-03-30 |

### CI Score Reference

| CI Range | Status | Behavior |
|----------|--------|---------|
| >= 70 | Trusted | Auto-approved execution |
| 40-69 | Normal | Standard 5-step workflow |
| 30-39 | Restricted | Explicit verification gate |
| < 30 | **BLOCKED** | Requires human review |

### CI Update Rules

| Event | CI Delta |
|-------|----------|
| Verified successful task | +5 |
| Failed or reverted task | -10 |
| Model Slop delivered | -10 |
| Hallucination detected | STOP + escalate |
| Full clean workflow (all 5 steps) | +15 |
| Dream Cycle completed | +10 |
| Archive failure (user data) | -20 + STOP |

---

## System Stats

| Metric | Value |
|--------|-------|
| Total Tasks | 2 |
| System Uptime | - |
| Dream Cycles | 0 |
| Last Dream | - |
| Overall System CI | 70.0 |

---

## Recent Activity Log

_Entries added after each /ship step._

| Date | Skill | Task | CI Delta | Notes |
|------|-------|------|----------|-------|
| 2026-03-30 | engine | System-wide installation v4.1.0 | +15 | install-global.sh, VS Code extension, PreLoadMemory fix |
| 2026-03-30 | context | OCTA workspace audit & fix | +5 | PreLoadMemory upgrade, missing files verified |
