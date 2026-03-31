# CONTRIBUTING.md — NEUTRON EVO OS Contribution Guide

> How to add skills, update CI, bump versions, and change governance.
> Maintained by: Adam Wang | Last Updated: 2026-03-31

---

## Adding a New Skill

A skill in NEUTRON EVO OS is a self-contained unit of capability with:
- A `SKILL.md` file (metadata + execution logic)
- A `logic/` module (implementable, Phase 5)
- A `validation/` module (Phase 5)

### 4 Steps to Add a Skill

#### Step 1 — Create the skill directory
```
skills/core/<skill-name>/
├── SKILL.md              ← REQUIRED (metadata + execution logic)
├── logic/
│   └── __init__.py       ← REQUIRED (even if stubbed)
└── validation/
    └── __init__.py       ← REQUIRED (even if stubbed)
```

#### Step 2 — Write `SKILL.md`
```markdown
---
name: <skill-name>
type: core          # or: "support", "learned"
version: 1.0.0
CI: 50              # Initial CI (starts at 50 for new skills)
dependencies: []   # List of other skill names this depends on
last_dream: null
---

## Execution Logic

### Purpose
<1-paragraph description of what this skill does>

### Entry Criteria
- What must be true before this skill executes?
- What context files must be loaded?

### Execution Steps
1. <Step description>
2. <Step description>

### Exit Criteria
- What must be true for the skill to declare success?
- What CI delta to apply on success/failure?

### CI Update
- Successful execution: **+5 CI**
- Failed or reverted: **-10 CI**
- Full clean workflow (all 5 steps): **+15 CI**
```

#### Step 3 — Register in `expert_skill_router.py`
Add the skill keyword mapping:
```python
SKILL_KEYWORDS = {
    # ... existing skills ...
    "<skill-name>": "<skill-name>",  # keyword → skill name
}
```

#### Step 4 — Update `PERFORMANCE_LEDGER.md`
Add the skill to the CI table:
```markdown
| <skill-name> | 50 | 0 | - |
```

Add an entry in Recent Activity Log:
```markdown
| YYYY-MM-DD | <skill-name> | New skill registered | +0 | Initial CI=50 |
```

---

## CI Update Protocol

CI (Credibility Index) reflects trust in each skill. It must be kept accurate.

### When to Update CI

| Event | Delta | Who Updates |
|-------|-------|-------------|
| Verified successful task | +5 | Agent (after /ship) |
| Failed or reverted task | -10 | Agent (after failure) |
| Model Slop delivered | -10 | Any agent who detects it |
| Hallucination detected | STOP + escalate | Any agent |
| Full clean 5-step workflow | +15 | Routing agent |
| Dream Cycle completed | +10 | Dream engine |
| Archive failure (user data) | -20 + STOP | Memory skill |
| New skill registered | +0 (starts at 50) | Contributor |

### How to Update CI

Run the audit command:
```bash
python3 -c "from engine.expert_skill_router import audit; import json; print(json.dumps(audit(), indent=2))"
```

Or use the Makefile:
```bash
make ci-audit   # View all CI scores
make ci-route TASK="<task description>"  # Route and see routing decision
```

### CI Score Reference

| Range | Status | Behavior |
|-------|--------|----------|
| ≥ 70 | Trusted | Auto-approved execution |
| 40–69 | Normal | Standard 5-step workflow |
| 30–39 | Restricted | Explicit verification gate |
| < 30 | **BLOCKED** | Requires human review |

---

## Version Bumping Checklist

When bumping NEUTRON EVO OS version (e.g., v4.1.0 → v4.2.0):

- [ ] Update `SOUL.md` header version
- [ ] Update `Makefile` help header (`NEUTRON-EVO-OS vX.Y.Z`)
- [ ] Update `install-global.sh` header and `SessionStart` echo string
- [ ] Update `engine/__init__.py` `__version__`
- [ ] Update `evolution_dashboard.py` ASCII art version
- [ ] Update `vscode-extension/templates/SOUL.md` version
- [ ] Update `~/.claude/CLAUDE.md` NEUTRON version reference
- [ ] Add entry in `HEARTBEAT.md` for the new version
- [ ] Run `make ci-audit` — verify no skill CI < 30 after changes
- [ ] Run `make test` — all tests pass
- [ ] Tag the release: `git tag vX.Y.Z && git push --tags`

---

## Governance Change Process

Governance changes (GOVERNANCE.md, RULES.md, this CONTRIBUTING.md) follow a
strict 4-step process:

### Step 1 — Proposal
Write a PR or issue with:
- **What** is changing (exact file + line)
- **Why** it is changing (justification, not just preference)
- **Impact** on existing skills and workflows

### Step 2 — Justification Required
Every governance change must cite:
- Which SOUL.md or MANIFESTO.md principle it serves
- Evidence of a real problem (bug, inconsistency, missing coverage)
- No solution that preserves the status quo at lower risk

### Step 3 — Peer Review
- Changes to core files (SOUL.md, MANIFESTO.md, GOVERNANCE.md) require review
- Reviewer: any agent with CI ≥ 70 on the `engine` skill
- Reviewer must verify: SOUL alignment, no CI manipulation, no authority creep

### Step 4 — Ratification
- After peer review: Adam Wang (system owner) approves and merges
- Document the decision in `HEARTBEAT.md`
- No governance change takes effect until logged in `HEARTBEAT.md`

### Emergency Override
In a genuine incident (data loss, security breach), any agent may enact
emergency changes without full review, but must:
1. Document the change and rationale immediately
2. Notify Adam Wang within 1 hour
3. Submit a full proposal within 24 hours for post-hoc ratification

---

## File Ownership

| File | Owner | Review Required |
|------|-------|----------------|
| SOUL.md | Adam Wang | Yes (all changes) |
| MANIFESTO.md | Adam Wang | Yes (all changes) |
| GOVERNANCE.md | Adam Wang | Yes (all changes) |
| RULES.md | Any trusted agent | Yes |
| PERFORMANCE_LEDGER.md | Any agent | Yes (peer verify CI math) |
| engine/*.py | Any agent | Yes |
| skills/core/*/SKILL.md | Skill owner | Yes |
| MemoryOS/** | Any agent | Yes |

---

## Bug Reports

To report a bug found during execution:
1. Log in `memory/YYYY-MM-DD.md`
2. Open a GitHub issue or create a `BUGFIX.md` entry
3. Tag it with: `bug`, `critical`/`high`/`medium`/`low`
4. Include: file path, line number, reproduction steps, impact

---

## Questions

For governance questions: re-read SOUL.md §Functional Credibility.
If still unclear: STOP_AND_ASK Adam Wang.
