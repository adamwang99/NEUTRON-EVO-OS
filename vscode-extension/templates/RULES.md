# RULES.md - NEUTRON EVO OS Operating Rules

> Governed by SOUL.md and MANIFESTO.md
> Last Updated: 2026-03-30

---

## Part 1: 5-Step Workflow

```
/explore  → Understand the problem space
/spec     → Define the specification
/build    → Implement
/verify   → Validate against spec
/ship     → Deliver and log
```

### /explore
- Read SOUL.md, MANIFESTO.md, USER.md
- Audit PERFORMANCE_LEDGER.md for relevant CI scores
- Identify skill dependencies
- Route to appropriate skills via expert_skill_router

### /spec
- Write formal specification
- Define acceptance criteria
- Identify constraints and risks
- Reference SOUL.md principles

### /build
- Implement against spec
- Follow design standards (DESIGN_SYSTEM.md)
- Archive before any deletion
- Log progress to /memory/

### /verify
- Validate against acceptance criteria
- Run tests
- Check for Model Slop (repetitive, low-quality, hallucinated output)
- Audit: does output earn CI?

### /ship
- Document changes
- Update PERFORMANCE_LEDGER.md
- Log to /memory/
- Execute Dream Cycle if triggered

---

## Part 2: Anti-Model-Slop Rules

**Definition**: Model Slop is any output that is:
- Repetitive or templated without functional purpose
- Hallucinated (fabricated facts, fake citations)
- Verbose without substance
- Mechanically compliant but intellectually hollow

**Enforcement**:
- Before delivering output, ask: "Does this earn CI?"
- Output must be verifiable, concise, and functionally valuable
- Never ship output you cannot defend with evidence

---

## Part 3: File Operations

### Before ANY edit
1. Archive to /memory/archived/ (not delete)
2. Copy to .backup/ with timestamp
3. Document reason for change

### Before deletion
1. Archive to /memory/archived/
2. Log deletion in PERFORMANCE_LEDGER.md
3. Require human approval if > 10 files

---

## Part 4: CI Workflow

Every task execution updates PERFORMANCE_LEDGER.md:
- CI starts at 50 for new skills
- +5 per verified successful task
- -10 per failed or reverted task
- CI >= 70: full trust, auto-approved
- CI < 30: requires explicit verification step

---

## Part 5: Context Loading Order

```
1. SOUL.md         → Identity & ∫f(t)dt philosophy
2. MANIFESTO.md     → Manifesto & core principles
3. USER.md         → User preferences
4. GOVERNANCE.md   → Policy rules
5. RULES.md        → Operating procedures (this file)
6. PERFORMANCE_LEDGER.md → CI audit
7. memory/         → Daily logs
```
