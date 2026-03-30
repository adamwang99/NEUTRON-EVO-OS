# 🧠 NEUTRON EVO OS

![Banner](https://raw.githubusercontent.com/adamwang99/NEUTRON-EVO-OS/main/NEUTRON%20EVO%20OS.png)

> **∫f(t)dt** — *Functional Credibility Over Institutional Inertia*
> Sovereign Intelligence Operating System for Claude CLI, Cursor, and all AI Context Windows

---

## Features

| Feature | Description |
|---------|-------------|
| **Memory Stack** | 10+ layered files: SOUL.md, MANIFESTO.md, GOVERNANCE.md, RULES.md, PERFORMANCE_LEDGER.md |
| **5-Step Workflow** | `/explore` → `/spec` → `/build` → `/verify` → `/ship` |
| **CI Tracking** | Every skill earns or loses CI via PERFORMANCE_LEDGER.md |
| **Anti-Model-Slop** | Strict output quality gates — no hallucination, no verbosity |
| **Dream Cycle** | Memory 2.0: auto-archive, prune noise, distill logs into Cookbooks |
| **System-Wide** | Apply ∫f(t)dt to ALL projects (existing & future) |

---

## System-Wide Installation ⭐ (Recommended)

Apply NEUTRON EVO OS to **every project** — current and future. One command.

```bash
# Option 1: From this repo
cd NEUTRON-EVO-OS && bash install-global.sh

# Option 2: Via Make
make install-global

# Option 3: Via VS Code Extension (recommended for GUI users)
code --install-extension vscode-extension/neutron-evo-os-4.1.0.vsix
```

### What gets installed globally:

| File | Purpose |
|------|---------|
| `~/.claude/settings.json` | Claude Code reads NEUTRON context at every session start |
| `~/.claude/CLAUDE.md` | Global fallback context — works in any workspace |
| `~/.neutron-evo-os/` | Full NEUTRON EVO OS repository |

### How it works:

1. **Claude Code starts** → reads `~/.claude/CLAUDE.md`
2. **SessionStart hook fires** → loads `NEUTRON_ROOT` context
3. **Every new workspace** → `NEUTRON EVO OS` extension auto-injects context files
4. **No manual setup needed** — works in `~/projects/`, `~/code/`, anywhere

> ⚠️ Restart any open Claude Code / VS Code sessions after installation.

---

## Quick Start (Local)

```bash
git clone https://github.com/adamwang99/NEUTRON-EVO-OS.git
cd NEUTRON-EVO-OS

make install        # pip + npm dependencies
make live           # Start observer + dashboard
make dream          # Run Dream Cycle manually
make test           # Run tests
make clean          # Remove cache files
```

---

## VS Code Extension

```bash
code --install-extension vscode-extension/neutron-evo-os-4.1.0.vsix
```

Features:
- **Auto-inject** context files when opening any folder
- **Quick Setup** command for configuration
- **Dream Cycle** trigger from Command Palette
- **System-wide** via global install script

Settings (`Settings > NEUTRON EVO OS`):
- `neutronEvoOs.autoInject` — Enable/disable auto-inject (default: true)
- `neutronEvoOs.templateSource` — `embedded` (works offline) or `external` (full context from NEUTRON_ROOT)
- `neutronEvoOs.excludePatterns` — Folders to skip (node_modules, .git, etc.)

---

## Architecture

```
NEUTRON-EVO-OS/
├── install-global.sh            ← System-wide installer ⭐
├── SOUL.md                     # Identity & ∫f(t)dt philosophy
├── MANIFESTO.md                # The NEUTRON EVO OS Manifesto
├── USER.md                     # User preferences
├── GOVERNANCE.md               # Policy rules & stop conditions
├── RULES.md                   # 5-step workflow & anti-Model-Slop rules
├── PERFORMANCE_LEDGER.md        # Skill CI (Credibility Index) tracking
├── CLAUDE.md                   # Auto-injected context for AI sessions
├── START.md                    # Quick reference
│
├── skills/core/                # Folder-based skill architecture
│   ├── context/               # Context loading & injection
│   ├── memory/               # Memory & Dream Cycle
│   ├── workflow/             # 5-step workflow execution
│   └── engine/              # Expert skill router
│
├── engine/                    # Core engine
│   ├── expert_skill_router.py  # CI audit & task routing
│   ├── smart_observer.py       # Watchdog + debounce
│   └── dream_engine.py         # Archive + prune + distill
│
├── memory/                    # Daily logs
│   ├── archived/            # Archived user data (NEVER DELETE)
│   └── cookbooks/           # Distilled knowledge
│
├── vscode-extension/          # VS Code extension + .vsix ⭐
└── evolution_dashboard.py      # Rich terminal CI dashboard
```

---

## 5-Step Workflow

```
/explore  → Audit CI, route skills, understand problem
/spec     → Write formal spec with measurable acceptance criteria
/build    → Implement against spec, archive before delete
/verify   → Validate against spec, check for Model Slop
/ship     → Update ledger, log, deliver summary
```

---

## CI (Credibility Index)

| CI Score | Status | Behavior |
|----------|--------|---------|
| >= 70 | Trusted | Auto-approved execution |
| 40-69 | Normal | Standard workflow |
| 30-39 | Restricted | Explicit verification gate |
| < 30 | **BLOCKED** | Requires human review |

---

## References

| File | Purpose |
|------|---------|
| `SOUL.md` | Identity, philosophy, constraints |
| `MANIFESTO.md` | ∫f(t)dt formalization, core principles |
| `RULES.md` | Operating procedures, anti-Model-Slop rules |
| `PERFORMANCE_LEDGER.md` | Live CI scores per skill |

---

## License

MIT — Adam Wang (Vương Hoàng Tuấn)
