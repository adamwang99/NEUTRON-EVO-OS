# NEUTRON EVO OS

This project runs on **NEUTRON EVO OS** — a sovereign intelligence operating system built on ∫f(t)dt: Functional Credibility Over Institutional Inertia.

## ⚡ Auto-Confirm System (CRITICAL)

**Before presenting ANY gate to the user, ALWAYS check auto-confirm first:**

```
1. Read memory/.auto_confirm.json
2. If {"enabled": true}:
   - discovery=true  → Skip discovery interview, use task directly
   - spec=true       → After writing SPEC → AUTO-APPROVE, go straight to /build
   - acceptance=true → After /build → AUTO-PASS, go straight to /ship
3. Only present gate UI if auto-confirm is FALSE for that specific gate
```

**Only /ship rating is ALWAYS requested** — even in auto mode.
Run `neutron auto full` to enable all gates auto-confirm.

## CRITICAL: File Backup Rule

**Before ANY file edit, agent MUST:**
1. Copy original file to `.backup/` folder first
2. THEN edit the file

Example: Before editing `src/api.ts` → First copy to `.backup/src/api.ts.backup`

## Context Files

For full context, read these files in order:
- **SOUL.md** — Identity, philosophy (∫f(t)dt), sovereignty & meritocracy principles
- **MANIFESTO.md** — The NEUTRON EVO OS Manifesto
- **USER.md** — User preferences
- **GOVERNANCE.md** — Policy rules
- **RULES.md** — Operating procedures (5-step workflow: /explore /spec /build /verify /ship)
- **DESIGN_SYSTEM.md** — Design standards
- **WORKFLOW.md** — Task workflow
- **PERFORMANCE_LEDGER.md** — Skill Credibility Index (CI) tracking
- **START.md** — Quick start guide

## 5-Step Workflow
```
/explore → /spec → /build → /verify → /ship
```
See RULES.md for full workflow definition.

## Skill Architecture
Skills live under `/skills/` in folder format (Anthropic style):
- `skills/core/context/` — Context management
- `skills/core/memory/` — Memory and recall
- `skills/core/workflow/` — Workflow execution
- `skills/core/engine/` — Expert skill router

## System-Wide Setup ⭐

Apply NEUTRON EVO OS to **all projects** (existing & future) with one command:

```bash
bash install-global.sh   # or: make install-global
```

This installs globally:
- `~/.claude/settings.json` — SessionStart hook loads NEUTRON context
- `~/.claude/CLAUDE.md` — Global fallback context for all sessions
- `~/.neutron-evo-os/` — Full NEUTRON EVO OS repo

VS Code Extension (recommended for GUI users):
```bash
code --install-extension vscode-extension/neutron-evo-os-4.1.0.vsix
```

See README.md for full system-wide installation guide.
