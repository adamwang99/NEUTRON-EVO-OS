---
name: context
type: core
version: 1.0.0
CI: 50
dependencies: []
last_dream: null
---

## Execution Logic

### Purpose
Manage context loading, injection, and priority for NEUTRON EVO OS across Claude CLI, Cursor, and IDE Context Windows.

### Loading Order (mandatory, top to bottom)
```
1. SOUL.md              → Identity & ∫f(t)dt philosophy
2. MANIFESTO.md         → Core principles
3. USER.md              → User preferences
4. GOVERNANCE.md        → Policy rules
5. RULES.md             → 5-step workflow & anti-Model-Slop rules
6. PERFORMANCE_LEDGER.md → CI audit
7. memory/YYYY-MM-DD.md → Daily logs
```

### Context Injection Rules
- **On session start**: Load SOUL.md, MANIFESTO.md, USER.md first — always
- **On task start**: Load RULES.md and PERFORMANCE_LEDGER.md before any skill execution
- **On IDE activation**: Read CLAUDE.md for project-specific overrides
- **On skill dispatch**: Inject skill-specific context from `/skills/<skill>/SKILL.md`

### Context Priority
| Priority | Content | TTL |
|----------|---------|-----|
| P0 | SOUL.md, MANIFESTO.md | Session |
| P1 | USER.md, GOVERNANCE.md, RULES.md | Session |
| P2 | PERFORMANCE_LEDGER.md | Per-task |
| P3 | Daily logs, learned context | Persistent |

### Anti-Hallucination
- On any API/library call: use Context Hub (`chub search`) or official docs before outputting code
- Never fabricate API parameters; always verify
- Flag and reject output where factual claims cannot be verified

### Claude CLI Compatibility
- Read `.claude/settings.json` for CLI-specific permissions
- Respect `permissions.allow` list for shell commands
- Do not exceed declared permission scopes

### Cursor / IDE Context Windows
- Inject context via CLAUDE.md in project root
- Stack-based layering: lower layers are always loaded first
- Learned skills from `/skills/learned/` are injected dynamically by engine

### CI Update
After any context skill execution:
- If context was loaded correctly with no hallucination: **+3 CI**
- If context was missing or corrupted (required rework): **-5 CI**
