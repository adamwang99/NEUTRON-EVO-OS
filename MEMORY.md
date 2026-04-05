# MEMORY.md - NEUTRON EVO OS Long-term Knowledge

## Memory Stack Files

| File | Purpose | Status |
|------|---------|--------|
| SOUL.md | Agent Identity & Constraints | ✅ |
| USER.md | User Preferences | ✅ |
| GOVERNANCE.md | Policy & Rules | ✅ |
| RULES.md | Operating Procedures | ✅ |
| WORKFLOW.md | Task Distribution & Parallel Processing | ✅ |
| MEMORY.md | This file - Long-term Knowledge | ✅ |
| MANIFESTO.md | ∫f(t)dt philosophy | ✅ |
| PERFORMANCE_LEDGER.md | CI tracking | ✅ |
| START.md | Quick reference | ✅ |
| HEARTBEAT.md | Session tracker | ✅ |
| memory/ | Daily logs | ✅ |
| memory/archived/ | Archived data (NEVER DELETE) | ✅ |
| memory/cookbooks/ | Distilled knowledge | ✅ |
| memory/LEARNED.md | Bug fixes & pattern database | ✅ |
| memory/discoveries/ | Project discovery sessions | ✅ |
| skills/core/ | Skill architecture | ✅ |
| engine/ | Core engine | ✅ |
| COORDINATION.md | Multi-Agent Workflow | ✅ |
| HEARTBEAT.md | Session Tracker | ✅ |

---

## Context Loading Order (MUST READ)

```
TRƯỚC KHI LÀM GÌ CŨNG PHẢI ĐỌC:
1. SOUL.md              → Agent identity, forbidden actions
2. USER.md              → User preferences
3. GOVERNANCE.md        → Policy rules, access control
4. RULES.md             → Operating procedures
5. WORKFLOW.md          → Task distribution & parallel processing
6. MANIFESTO.md         → ∫f(t)dt philosophy
7. MEMORY.md            → Long-term knowledge
8. memory/LEARNED.md    → Past bugs fixed, patterns to avoid ← NEW SESSIONS READ THIS
9. memory/YYYY-MM-DD.md → Today's context
```

---

## Key Learnings

### Claude Code Integration
- Memory stack works with Claude Code extension in VS Code
- Use @-mentions for quick context: `@SOUL.md`, `@GOVERNANCE.md`
- SessionStart hook loads NEUTRON context automatically
- PreToolUse hook backs up files before any edit

### Workflow
- Daily session: read today's memory file first
- After session: append log to daily file
- Key learnings: update this file

### VS Code Setup
- Install: Claude Code extension (anthropic.claude-code)
- Open folder containing memory stack
- Use Ctrl+Shift+P → "Claude Code" to start

---

## Governance Integration

### From RULE for CODING
- ✅ GOVERNANCE.md - Policy rules
- ✅ RULES.md - Operating procedures
- ✅ COORDINATION.md - Multi-agent workflow

### Key Rules Summary
- **Forbidden**: Hard delete, modify production without test, skip backup
- **Required**: Backup before modify, approval > 100 records
- **Stop conditions**: Policy conflict, backup failure, data loss

---

## Recurring Patterns
- Trading signals analysis
- Code development tasks
- Multi-agent coordination
- System automation

---

## Reference

| File | Purpose |
|------|---------|
| memory/ | Daily session logs |
| skills/core/ | Skill implementations |
| engine/ | Skill router, observer, dream engine |
| .claude/ | Claude Code settings |
| .vscode/ | VS Code workspace settings |

## Quick Start
```bash
# 1. Open VS Code
File → Open Folder → ai-context-master

# 2. Read START.md for quick reference

# 3. Run: make live   (start observer)
# 4. Run: make dream  (manual Dream Cycle)
```

## Auto-Apply Global Settings

### Option 1: Auto Install (Recommended)
```bash
# Run from NEUTRON repo root
bash install-global.sh
```

### Option 2: VS Code Extension
```bash
code --install-extension vscode-extension/neutron-evo-os-4.1.0.vsix
```

### Kết quả
- ✅ Memory Stack tự động load trong mọi dự án
- ✅ Claude Code đọc SOUL.md, USER.md, GOVERNANCE.md...
- ✅ Parallel tasks enabled
