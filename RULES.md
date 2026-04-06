# RULES.md — NEUTRON EVO OS Operating Rules

---

## 🚨 Upgrade Protection Protocol

**Triggered by:** `git pull`, `git checkout`, `git merge`, `pip install`, `npm install`, any install script.

**BEFORE any upgrade:**
```
1. git status  ← MUST check what will be modified
2. Protect data files: .env, memory/*.json, USER.md, memory/rss*.json
3. Backup to .backup/:  cp .env .backup/.env.$(date +%Y%m%d%H%M%S)
4. If file exists in both git AND local:
   → Local has real data: git checkout --ours <file>
5. AFTER upgrade: verify all protected files still have correct content
```

**FORBIDDEN during upgrade:**
- ❌ `git reset --hard` without checking protected files
- ❌ `git checkout --force` without verification
- ❌ Overwriting `.env` without verifying API keys intact

---

## Archive Protocol

- **MANDATORY** before any modification or deletion
- User data: **NEVER DELETE** → move to `memory/archived/`
- Archive format: `YYYY-MM-DD_HH-MM-SS_module.original_name`
- Keep minimum 7 most recent versions
- Delete old backups after 30 days

---

## 7-Step Workflow

```
/explore → /discovery → /spec (USER REVIEW) → /build → /verify → /acceptance → /ship
```

| Step | Gate | CI Delta |
|------|------|---------|
| explore | Auto | +5 |
| discovery | Human/auto | +5 |
| spec | **USER REVIEW** | +5 |
| build | SPEC check + LEARNED recall | +5 |
| verify | pytest + coverage ≥80% | +5 |
| acceptance | **USER CONFIRM** | +10 |
| ship | distill + archive | +15 |

---

## Anti-Model-Slop Rules

**Model Slop** = repetitive, hallucinated, hollow, mechanically compliant without substance.

**Before delivering output, ask:**
1. Can I defend this with evidence?
2. Is this the minimum sufficient answer?
3. Does this earn CI or just consume tokens?

CI impact: verified output **+5 CI** | Model Slop **-10 CI**

---

## Testing Requirements

- [ ] `pytest` passes
- [ ] Backup/restore verified
- [ ] No regression on old features
- [ ] Output is verifiable (not hallucinated)

---

## Quick Reference

```
BEFORE ANY UPGRADE:  git status → protect .env, memory/*.json → backup
BEFORE ANY EDIT:     cp file .backup/filename.timestamp
BEFORE ANY DELETE:   move to memory/archived/ (never hard delete)
BEFORE ANY OUTPUT:   Can I defend this? Is it minimum sufficient?
WORKFLOW:            explore → spec → build → verify → acceptance → ship
FORBIDDEN:            git reset --hard, Model Slop, hard delete user data
```
