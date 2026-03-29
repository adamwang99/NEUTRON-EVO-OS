# 🧠 NEUTRON EVO OS

![Banner](https://raw.githubusercontent.com/adamwang99/NEUTRON-EVO-OS/main/AI%20CONTEXT%20MASTER.png)

> **∫f(t)dt** — *Functional Credibility Over Institutional Inertia*
> Sovereign Intelligence Operating System for Claude CLI, Cursor, and all AI Context Windows

---

## Overview

**NEUTRON EVO OS** is a sovereign intelligence operating system built on two core principles:

- **Sovereignty**: No institutional inertia. No process for process's sake. Only functional output.
- **Meritocracy**: Credibility is earned through verified performance — CI (Credibility Index) is never granted, only earned.

It governs context, memory, and skill execution for every AI session across Claude CLI, Cursor, and IDE Context Windows.

---

## Features

| Feature | Description |
|---------|-------------|
| **Memory Stack** | 10+ layered files: SOUL.md, MANIFESTO.md, GOVERNANCE.md, RULES.md, PERFORMANCE_LEDGER.md |
| **5-Step Workflow** | `/explore` → `/spec` → `/build` → `/verify` → `/ship` |
| **CI Tracking** | Every skill earns or loses CI via PERFORMANCE_LEDGER.md |
| **Anti-Model-Slop** | Strict output quality gates — no hallucination, no verbosity |
| **Dream Cycle** | Memory 2.0: auto-archive, prune noise, distill logs into Cookbooks |
| **Expert Skill Router** | Routes tasks to skills based on CI audit |
| **Folder-Based Skills** | Anthropic-style skill architecture under `/skills/` |
| **Evolution Dashboard** | Rich terminal UI showing real-time CI scores |
| **Claude CLI Compatible** | Reads CLAUDE.md, respects `.claude/settings.json` |
| **IDE Context Windows** | Cursor, Copilot, and all AI Assistants via auto-inject |

---

## Quick Start

```bash
# Clone
git clone https://github.com/adamwang99/NEUTRON-EVO-OS.git
cd NEUTRON-EVO-OS

# Install dependencies
make install

# Start observer + dashboard
make live

# Run Dream Cycle manually
make dream
```

Or install the VS Code extension (see `vscode-extension/`):

```bash
code --install-extension vscode-extension/neutron-evo-os-4.0.0.vsix
```

---

## Architecture

```
NEUTRON-EVO-OS/
├── SOUL.md                    # Identity & ∫f(t)dt philosophy
├── MANIFESTO.md               # The NEUTRON EVO OS Manifesto
├── USER.md                    # User preferences
├── GOVERNANCE.md              # Policy rules & stop conditions
├── RULES.md                   # 5-step workflow & anti-Model-Slop rules
├── PERFORMANCE_LEDGER.md       # Skill CI (Credibility Index) tracking
├── CLAUDE.md                  # Auto-injected context for AI sessions
├── START.md                   # Quick reference
│
├── skills/                   # Folder-based skill architecture
│   └── core/
│       ├── context/          # Context loading & injection skill
│       ├── memory/          # Memory & Dream Cycle skill
│       ├── workflow/        # 5-step workflow execution
│       └── engine/         # Expert skill router
│
├── engine/                  # Core engine components
│   ├── expert_skill_router.py   # CI audit & task routing
│   ├── smart_observer.py        # Watchdog + debounce
│   └── dream_engine.py          # Archive + prune + distill
│
├── memory/                  # Daily logs
│   ├── archived/            # Archived user data (NEVER DELETE)
│   └── cookbooks/           # Distilled knowledge summaries
│
├── evolution_dashboard.py    # Rich terminal CI dashboard
├── Makefile                 # Shortcuts: make live, make dream, make test
└── requirements.txt          # Python: watchdog, rich
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

Each step is a gate — the next step does not begin until the current step is verified complete.

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
| `skills/core/*/SKILL.md` | Skill execution logic (YAML + Markdown) |

---

## License

MIT — Adam Wang (Vương Hoàng Tuấn)
