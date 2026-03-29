---
name: memory
type: core
version: 1.0.0
CI: 50
dependencies: []
last_dream: null
---

## Execution Logic

### Purpose
Manage long-term memory, daily logs, and Memory 2.0 (Dream Cycle: pruning + distillation) for NEUTRON EVO OS.

### Memory Architecture
```
memory/
├── YYYY-MM-DD.md     → Daily logs (append-only)
├── archived/          → Archived user data (NEVER DELETE)
│   └── *.log         → Timestamped archived logs
├── cookbooks/         → Distilled knowledge summaries
│   └── *.md          → Compressed topic summaries
└── learned/          → Learned skill patterns (via engine)
```

### Daily Log Protocol
- **Session start**: Read `memory/YYYY-MM-DD.md` (today's log)
- **Session end**: Append session summary to `memory/YYYY-MM-DD.md`
- **Format**: ISO timestamp + task + outcome + key learnings

### Log Entry Format
```markdown
## [HH:MM] — Task: <brief description>
- Action: <what was done>
- Outcome: <result>
- CI delta: <+/-N>
- Notes: <anything worth remembering>
```

### Archive Protocol (CRITICAL)
- **User data**: ALWAYS move to `/memory/archived/` — never hard delete
- **System noise**: `.tmp`, `.cache` files can be pruned after 3 days without references
- **Format**: `YYYY-MM-DD_HH-MM-SS_original-name.ext`
- Archive before any modification or deletion operation

### Dream Cycle (Memory 2.0)
Triggered by Smart Observer when work settles (30s debounce):

1. **Archive Phase**: Copy current logs to `/memory/archived/` with timestamp
2. **Prune Phase**: Remove `.tmp`/`.cache` files older than 3 days
3. **Distill Phase**: Compress repetitive patterns into Cookbooks
4. **Update**: Set `last_dream` in this SKILL.md header

### Retrieval
- Daily logs: `memory/YYYY-MM-DD.md`
- Topic search: grep over `memory/` directory
- Cookbooks: `memory/cookbooks/<topic>.md`
- Archived: `memory/archived/*.log`

### CI Update
After any memory skill execution:
- Log written without error: **+2 CI**
- Archive completed without data loss: **+3 CI**
- Dream Cycle executed successfully: **+10 CI** (system-level skill)
- User data accidentally deleted (not archived): **-20 CI + STOP**
