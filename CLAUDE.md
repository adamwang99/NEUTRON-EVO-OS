# NEUTRON EVO OS

This project runs on **NEUTRON EVO OS** — a sovereign intelligence operating system built on ∫f(t)dt: Functional Credibility Over Institutional Inertia.

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
