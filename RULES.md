# RULES.md - Agent Operating Rules

> Extracted from `RULE for CODING/Singler Agent/SYSTEM_PROMPT_BASE.txt`
> Combined with Parallel Coding Workflow
> Last Updated: 2026-03-10

---

## Part 1: Core Agent Rules

### Data Handling

#### 📋 Backup Protocol
- **AUTOMATIC** backup BEFORE any data modification or deletion
- Filename format: `YYYY-MM-DD_HH-MM-SS_MODULE_v[version].backup`
- Storage: `/backups/` (local) + Cloud backup
- Keep minimum 3 most recent versions
- Delete old backups after 30 days

#### 🗑️ Deletion Protocol
- **SOFT DELETE FIRST**: Mark as "deleted" instead of physical removal
- Wait 7 days before permanent deletion
- Require approval if deleting > 100 records
- Mandatory audit log: timestamp, user_id, reason, rows_affected, backup_location

#### ✏️ Modification Protocol
- ALWAYS test in staging environment FIRST
- **MANDATORY: Backup BEFORE any modification**
  - For file changes: Copy original file to `.backup/` folder BEFORE editing
  - Format: `YYYY-MM-DD_HH-MM-SS_original-filename.backup`
- NEVER modify without backup (this is CRITICAL)
- Document change reason in commit message
- Update CHANGELOG.md with change summary

#### 💾 File Backup Rule (CRITICAL)
**Agent MUST do this BEFORE any file edit:**
```
1. COPY file → .backup/filename.timestamp.ext
2. THEN edit the file
```

Example:
- Before editing `src/api.ts` → First copy to `.backup/src/api.ts.2026-03-17.backup`
- This applies to ALL files: .ts, .js, .json, .md, .py, etc.

---

### Testing Requirements

Before deploying ANY change:
- [ ] Unit tests pass (`test_*.py`)
- [ ] Integration tests pass (no data loss)
- [ ] Staging environment test
- [ ] Backup/restore test
- [ ] Performance test (tokens per task OK?)
- [ ] Regression test (old features still work?)
- [ ] Error handling test

---

### Monitoring & Alerts

#### Track Continuously
- Tokens per task (target: <500)
- Cost per run (target: <$0.01 per 100 records)
- Error rate (target: <0.1%)
- Failed backup detection
- Unusual activity patterns

#### Alert Conditions
- ⚠️ Token usage 2x normal → Investigate prompt efficiency
- ⚠️ Backup failures → Stop all write operations
- ⚠️ Error rate > 1% → Rollback latest changes
- ⚠️ Unusual access patterns → Security audit

---

## Part 2: Parallel Coding Workflow

### VS Code Multi-Root Workspace

```
Workspace Structure:
├── project1_trading-bot/    (CCXT + TA-Lib)
├── project2_ai-agent/      (Ollama + Memory)
├── .vscode/settings.json
└── parallel.code-workspace
```

### Opening Workspace
```bash
# In VS Code:
File → Open Workspace from File → parallel.code-workspace
```

### Parallel Features

| Feature | Shortcut | Usage |
|---------|----------|-------|
| Split Editor | `Ctrl+\` | View 2 files side by side |
| Multi Cursor | `Alt+Click` | Edit multiple locations |
| Terminal Tabs | `Ctrl+Shift+`` | Run multiple processes |
| Find & Replace | `Ctrl+Shift+H` | Replace across files |

---

### Multi-Agent Task Template

When assigning parallel tasks to Claude:

```
TRƯỚC KHI LÀM GÌ:
1. Đọc ../SOUL.md → Hiểu identity & constraints
2. Đọc ../USER.md → Biết preferences
3. Đọc ../GOVERNANCE.md → Follow rules
4. Đọc ../COORDINATION.md → Multi-agent workflow

TASK PARALLEL:
- [Task 1 for project1]
- [Task 2 for project2]

SAU SESSION:
- Log vào memory/YYYY-MM-DD.md
- Update MEMORY.md nếu có key learnings
```

---

### Claude Code Integration

#### Context Loading Order
```
1. SOUL.md         → Agent identity & constraints
2. USER.md         → User preferences
3. GOVERNANCE.md   → Policy & rules
4. RULES.md        → Operating procedures
5. COORDINATION.md → Multi-agent workflow
6. MEMORY.md       → Long-term knowledge
7. memory/YYYY-MM-DD.md → Today's context
```

#### @-Mentions Usage
```
@SOUL.md           → Inject identity
@GOVERNANCE.md     → Inject policy rules
@memory/2026-03-10.md → Today's logs
```

---

### Running Parallel Tasks

#### Terminal Workflow
```bash
# Terminal 1: Trading Bot
cd project1_trading-bot
python main.py

# Terminal 2: AI Agent
cd project2_ai-agent
python main.py

# Terminal 3: Monitor logs
tail -f logs/*.log
```

#### Claude Prompt for Parallel Generation
```
@memory "Generate parallel implementations:
1. Bot v1: CCXT + TA-Lib signal detection
2. Agent v1: Ollama + memory context

Output:
- project1_trading-bot/main.py
- project2_ai-agent/main.py
- Common utilities shared"
```

---

## Quick Reference

```
┌──────────────────────────────────────────────────────────┐
│ AGENT RULES QUICK REF                                    │
├──────────────────────────────────────────────────────────┤
│ BEFORE ANY ACTION:                                       │
│   □ Backup first (if modifying data)                    │
│   □ Check access control (GOVERNANCE.md)               │
│   □ Get approval if > 100 records                      │
│                                                          │
│ FORBIDDEN:                                              │
│   ✗ Hard delete data                                    │
│   ✗ Modify production without staging test              │
│   ✗ Skip backup                                         │
│                                                          │
│ PARALLEL:                                               │
│   → Use parallel.code-workspace                         │
│   → Split editor for review                             │
│   → Terminal tabs for running                           │
└──────────────────────────────────────────────────────────┘
```

---

## Part 3: UI Design Standards

All UI/frontend tasks must follow these rules:

- **Consistency**: All new interfaces must follow colors and spacing in `DESIGN_SYSTEM.md`
- **Frameworks**: Use Shadcn/ui or Tailwind CSS
- **Verification**: AI must verify responsive layout before completing task
- **Accessibility**: Ensure WCAG AA compliance (contrast ratio ≥ 4.5:1)
