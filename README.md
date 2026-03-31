# 🧠 NEUTRON EVO OS

![Banner](https://raw.githubusercontent.com/adamwang99/NEUTRON-EVO-OS/main/NEUTRON%20EVO%20OS.png)

> **∫f(t)dt** — *Functional Credibility Over Institutional Inertia*
> Sovereign AI Agent Operating System v4.1.0

---

## What Is This?

NEUTRON EVO OS is an autonomous operating system that runs on top of any AI CLI agent (Claude Code, Cursor, Cline) or any AI context window. It gives the AI a **soul**, **memory**, **discipline**, and **credibility system** — so it stops hallucinating, stops slopping, and starts delivering.

It is **not** a wrapper script. It is a complete cognitive architecture:
- 7 fully operational skills
- Full pipeline: Discovery → SPEC → Build → Acceptance → Ship
- User-rating-based CI (Credibility Index)
- Dream Cycle memory consolidation
- MCP server for AI Code integration
- NEUTRON CLI with 18 commands

---

## Features

| Feature | Description |
|---------|-------------|
| **7 Core Skills** | context, memory, workflow, engine, checkpoint, discovery, acceptance_test |
| **Discovery Interview** | 12-question hybrid interview to extract real requirements |
| **SPEC Review Gate** | Formal spec with measurable acceptance criteria — user must approve |
| **Acceptance Test Gate** | Auto-generated test script — user must confirm pass |
| **User Rating CI** | Shipments rated 1-5; average rating drives system credibility |
| **USER DECISIONS Log** | Only human decisions preserved, not skill executions |
| **Auto-Confirm Modes** | Skip gates individually or all at once (full, spec_only, acceptance_only, etc.) |
| **Dream Cycle** | Auto-archive + distill logs into knowledge |
| **MCP Server** | 10 tools exposed via stdio JSON-RPC 2.0 for Claude Code |
| **NEUTRON CLI** | 18 commands: run, discover, spec, build, accept, ship, auto, audit... |
| **System-Wide** | Apply ∫f(t)dt to ALL projects |

---

## Quick Install (2 minutes)

```bash
# 1. Clone
git clone https://github.com/adamwang99/NEUTRON-EVO-OS.git
cd NEUTRON-EVO-OS

# 2. Install (3 modes — pick one)
bash install.sh cli      # CLI only (neutron command)
bash install.sh mcp     # CLI + MCP server for Claude Code  ← recommended
bash install.sh full    # Everything: MCP + hooks + all projects

# 3. Verify
neutron --help
neutron status
```

**That's it.** No `pip install`, no config files, no credentials needed.

What it does:
- Installs `neutron` CLI to `~/.local/bin`
- Sets `~/.claude/CLAUDE.md` so every Claude Code session starts with NEUTRON context
- Works in any project directory, forever

---

## NEUTRON CLI — 18 Commands

```
neutron run <task>           Run full pipeline (explore → discovery → spec → build → accept → ship)
neutron discover "idea"     Start 12-question discovery interview
neutron discover-record      Record answers as key=value pairs
neutron spec [task]         Write SPEC.md (USER REVIEW gate)
neutron spec-approve        Approve SPEC — unlocks build
neutron build [task]        Build implementation
neutron verify [task]       Run verification
neutron accept prepare      Generate acceptance test script
neutron accept pass         Confirm acceptance
neutron ship --rating 4     Ship delivery (rating 1-5)
neutron auto full           Skip ALL gates (auto-confirm everything)
neutron auto spec_only      Auto-approve SPEC only
neutron auto disable        Full human control
neutron checkpoint          Write session checkpoint
neutron status              System status + health
neutron audit               Full CI audit (7 skills)
neutron memory log|search|status|dream|archive
neutron log                 Show today's memory log
neutron decisions           Show recent user decisions
neutron route <task>        Route task to best skill
neutron dream               Run Dream Cycle
```

---

## The Pipeline

```
/discover  →  12-question interview  →  DISCOVERY.md
    ↓
/spec      →  Formal SPEC.md          →  USER MUST APPROVE ⛔
    ↓
/build     →  Implementation          →  Anti-Slop enforcement
    ↓
/accept    →  Acceptance test        →  USER MUST CONFIRM ⛔
    ↓
/ship      →  Deliver + Rate          →  Rating updates CI
```

### Gates

Every pipeline gate is a **hard stop** unless auto-confirm is enabled:

| Gate | Normal Mode | Auto Mode |
|------|-------------|-----------|
| Discovery | 12 questions | Skipped |
| SPEC Review | User must approve | Auto-approved |
| Acceptance Test | User must confirm | Auto-passed |

---

## CI — Credibility Index

Every skill earns CI through real deliveries:

| Rating | CI Delta |
|--------|----------|
| Ship with rating 5 | +15 |
| Ship with rating 4 | +10 |
| Ship with rating 3 | +5 |
| Ship with rating 2 | -5 |
| Ship with rating 1 | -15 |

**User rating is the primary CI signal.** Skill execution counts are secondary.

---

## MCP Server — AI Code Integration

Connect NEUTRON to Claude Code as an MCP server:

```json
// ~/.claude/mcp.json
{
  "mcpServers": {
    "NEUTRON-EVO-OS": {
      "command": "python3",
      "args": ["-m", "mcp_server"],
      "env": { "NEUTRON_ROOT": "/path/to/NEUTRON-EVO-OS" }
    }
  }
}
```

10 MCP tools available:
- `neutron_checkpoint` — Write, read, handoff session checkpoint
- `neutron_discovery` — Run discovery interview
- `neutron_context` — Audit context files
- `neutron_memory` — Log, archive, search, dream, status
- `neutron_workflow` — Execute any pipeline step
- `neutron_acceptance` — Prepare or pass acceptance test
- `neutron_engine` — Audit CI, route tasks, control observer
- `neutron_audit` — Full system health check
- `neutron_auto_confirm` — Enable/disable auto-confirm modes

---

## Architecture

```
NEUTRON-EVO-OS/
├── engine/                          # Core engine
│   ├── expert_skill_router.py      # CI audit & task routing
│   ├── skill_execution.py          # Pipeline: validate → execute → log → update CI
│   ├── skill_registry.py           # Registry of all skills
│   ├── smart_observer.py           # Watchdog with debounce
│   ├── dream_engine.py             # Archive + distill cycle
│   ├── auto_confirm.py             # Gate skip configuration
│   ├── user_decisions.py           # USER DECISIONS tracker
│   ├── rating.py                   # Shipment rating tracker
│   ├── checkpoint_cli.py           # Checkpoint handoff
│   └── cli/
│       └── main.py                 # CLI entry point (18 commands)
│
├── skills/core/                     # 7 fully implemented skills
│   ├── context/                   # Context loading & P0/P1/P2 injection
│   ├── memory/                    # Memory ops + Dream Cycle trigger
│   ├── workflow/                   # Full pipeline + gate management
│   ├── engine/                    # Audit + route + observer control
│   ├── checkpoint/                # Write/read/handoff checkpoint
│   ├── discovery/                 # 12-question hybrid interview
│   └── acceptance_test/           # Auto-generated test + user confirm
│
├── memory/                         # Daily logs
│   ├── archived/                   # Archived files (NEVER DELETE)
│   ├── discoveries/               # Discovery session outputs
│   └── cookbooks/                 # Distilled knowledge
│
├── mcp_server/                     # MCP stdio server (10 tools)
│   ├── transport.py               # JSON-RPC 2.0 stdio
│   ├── tools.py                   # NEUTRON tools as MCP
│   ├── resources.py               # Memory + ledger as MCP resources
│   └── prompts.py                 # Workflow prompts as MCP prompts
│
├── install-cli.sh                  # Install `neutron` command ⭐
├── install-global.sh               # System-wide install
├── .mcp.json                      # MCP config for Claude Code
└── Makefile                        # Dev commands
```

---

## Reference

| File | Purpose |
|------|---------|
| `SOUL.md` | Identity, philosophy, constraints |
| `MANIFESTO.md` | ∫f(t)dt formalization |
| `GOVERNANCE.md` | Policy rules & stop conditions |
| `RULES.md` | Operating procedures & anti-Model-Slop rules |
| `PERFORMANCE_LEDGER.md` | Live CI scores per skill |
| `USER.md` | User preferences & project context |

---

## Development

```bash
make install          # pip + npm dependencies
make test            # Run pytest
make lint            # Run flake8
make clean           # Remove cache

# CLI targets
make cli-install     # bash install-cli.sh
make cli-status      # neutron status
make cli-audit      # neutron audit
make cli-discover    # neutron discover

# MemoryOS CLI
make memoryos-init   # node MemoryOS/src/index.js init
make memoryos-wake   # node MemoryOS/src/index.js wake
make memoryos-context # node MemoryOS/src/index.js context
```

---

## License

MIT — Adam Wang (Vương Hoàng Tuấn)
