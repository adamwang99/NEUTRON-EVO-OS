# 🚀 START.md - NEUTRON EVO OS Quick Reference

> ∫f(t)dt — Functional Credibility Over Institutional Inertia
> Last Updated: 2026-03-30

---

## 1. Open Workspace

```bash
# VS Code
File → Open Folder → NEUTRON-EVO-OS
```

---

## 2. 5-Step Workflow

```
/explore  → Understand the problem space
/spec     → Define the specification
/build    → Implement
/verify   → Validate against spec
/ship     → Deliver and log
```

### Quick Reference

| Step | Action |
|------|--------|
| /explore | Read SOUL.md, MANIFESTO.md, USER.md, audit PERFORMANCE_LEDGER.md |
| /spec | Write formal spec, define acceptance criteria |
| /build | Implement, archive before delete |
| /verify | Run tests, check for Model Slop |
| /ship | Update ledger, log to /memory/, trigger Dream Cycle if needed |

---

## 3. Context Loading Order

```
1. SOUL.md              → Identity & ∫f(t)dt philosophy
2. MANIFESTO.md          → Core principles
3. USER.md              → User preferences
4. GOVERNANCE.md        → Policy rules
5. RULES.md             → Operating procedures (5-step workflow)
6. PERFORMANCE_LEDGER.md → CI audit
7. memory/YYYY-MM-DD    → Daily logs
```

---

## 4. File Quick Reference

| File | Purpose |
|------|---------|
| SOUL.md | Identity, philosophy, constraints |
| MANIFESTO.md | ∫f(t)dt manifesto, core principles |
| USER.md | User preferences |
| GOVERNANCE.md | Policy rules, stop conditions |
| RULES.md | 5-step workflow, anti-Model-Slop rules |
| PERFORMANCE_LEDGER.md | Skill CI tracking |
| skills/ | Folder-based skill architecture |
| engine/ | Skill router, observer, dream engine |
| memory/ | Daily logs |
| memory/archived/ | Archived user data (NEVER DELETE) |
| memory/cookbooks/ | Distilled knowledge summaries |

---

## 5. CI (Credibility Index) Rules

| CI Score | Status | Action |
|----------|--------|--------|
| >= 70 | Full trust | Auto-approved execution |
| 40-69 | Normal | Standard workflow |
| < 40 | Restricted | Explicit verification step |

---

## 6. Emergency Checklist

```
□ STOP if: Policy conflict
□ STOP if: Archive failure
□ STOP if: Data loss detected
□ STOP if: Low confidence (< 0.7)
□ ASK if: Unclear requirements
□ ARCHIVE before delete (never hard delete user data)
□ APPROVAL if: > 100 records affected
```

---

## 7. Commands

```bash
# Dream Cycle (manual)
make dream

# Start observer + dashboard
make live

# Install dependencies
make install

# Run tests
make test

# Clean cache
make clean
```

---

## 8. Skill Architecture

```
skills/
├── core/
│   ├── context/   — Context management skill
│   ├── memory/    — Memory & recall skill
│   ├── workflow/ — 5-step workflow execution
│   └── engine/   — Expert skill router
└── learned/      — Future learned skills
```

---

**Ready to build.** — NEUTRON EVO OS v4.0.0
