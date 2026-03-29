# MEMORY.md - NEUTRON EVO OS Long-term Knowledge

## Memory Stack Files

| File | Purpose | Priority |
|------|---------|----------|
| SOUL.md | Agent Identity & Constraints | 1 |
| USER.md | User Preferences | 1 |
| GOVERNANCE.md | Policy & Rules (from policy.json) | 1 |
| RULES.md | Operating Procedures | 1 |
| COORDINATION.md | Multi-Agent Workflow | 1 |
| WORKFLOW.md | Task Distribution & Parallel Processing | 1 |
| CH.md | Context Hub (API Docs Layer) | 1 |
| MEMORY.md | This file - Long-term Knowledge | - |
| HEARTBEAT.md | Session Tracker | - |
| memory/ | Daily Logs | - |
| Parallel/ | Multi-project Workspace | - |
| context-hub/ | API Docs Cache | - |
| MemoryOS/ | Full Memory OS | - |
| .claude/agents/ | Subagents | - |
| ULTIMATE_PROMPT.md | Agent Factory Prompt | - |
| NEUTRON_EVO_OS.md | System Prompt for AI Agents | - |

---

## Context Loading Order (MUST READ)

```
TRƯỚC KHI LÀM GÌ CŨNG PHẢI ĐỌC:
1. SOUL.md         → Agent identity, forbidden actions
2. USER.md         → User preferences
3. GOVERNANCE.md   → Policy rules, access control
4. RULES.md        → Operating procedures
5. COORDINATION.md → Multi-agent workflow
6. WORKFLOW.md     → Task distribution & parallel processing ⭐
7. CH.md           → Context Hub usage guide
7. MEMORY.md       → Long-term knowledge
8. memory/YYYY-MM-DD.md → Today's context
9. context-hub/   → API docs (on-demand via chub search)
```

### Context Hub (Layer 8 - API Ground Truth)

**Khi dùng external API (OpenAI, AWS, CCXT, Stripe...):**

```bash
# Option 1: Khi có context-hub
chub search "[API provider] [function]"
chub get [DOC_ID] --lang python

# Option 2: Web search (hiện tại dùng)
Web search: "[API provider] official documentation Python"
```

**Tại sao:**
- Tránh hallucinate API parameters
- Dùng đúng API version
- Code chính xác từ ground truth

---

## Key Learnings

### Claude Code Integration
- Memory stack works with Claude Code extension in VS Code
- Use @-mentions for quick context: `@SOUL.md`, `@GOVERNANCE.md`
- Manual read for full context

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
- ✅ GOVERNANCE.md - Policy rules (from policy.json)
- ✅ RULES.md - Operating procedures (from SYSTEM_PROMPT_BASE.txt)
- ✅ COORDINATION.md - Multi-agent workflow (from coordination.md)

### Key Rules Summary
- **Forbidden**: Hard delete, modify production without test, skip backup
- **Required**: Backup before modify, approval > 100 records
- **Stop conditions**: Policy conflict, backup failure, data loss

---

## Parallel Coding Workflow

### Workspace Structure
```
Parallel/
├── parallel.code-workspace     ← Open this!
├── .vscode/settings.json
├── project1_trading-bot/      (CCXT + TA-Lib)
└── project2_ai-agent/        (Ollama + Memory)
```

### VS Code Shortcuts
| Action | Shortcut |
|--------|----------|
| Claude Code | Ctrl+Shift+P → "Claude Code" |
| New terminal | Ctrl+Shift+` |
| Split editor | Ctrl+\ |
| Multi-cursor | Alt+Click |
| Find in files | Ctrl+Shift+F |

### Parallel Task Template
```
TRƯỚC KHI LÀM GÌ:
1. Đọc SOUL.md, USER.md, GOVERNANCE.md, COORDINATION.md

TASK:
- [Task 1: Trading Bot]
- [Task 2: AI Agent]

SAU XONG:
- Log to memory/YYYY-MM-DD.md
- Update MEMORY.md if key learnings
```

---

## Recurring Patterns
- Trading signals analysis
- Code development tasks
- Multi-agent coordination
- System automation

---

## Reference
- See memory/ folder for daily logs
- See HEARTBEAT.md for session tracking
- See Parallel/ for multi-project workspace
- See CH.md for Context Hub integration
- See START.md for quick reference
- See docs/ for API documentation links
- See templates/ for code templates
- See WORKFLOW.md for task distribution
- See COORDINATION.md for parallel agent coordination
- See MemoryOS/ for full memory OS
- See RULE for CODING/ for source governance docs
- See .claude/agents/ for Subagents
- See ULTIMATE_PROMPT.md for agent factory prompt

## Quick Start
```bash
# 1. Open VS Code
File → Open Folder → MEMORY cho Agent Coding

# 2. Read START.md for quick reference

# 3. Copy prompt template and start coding!
```

## Auto-Apply Global Settings

### Option 1: Auto Install (Recommended)
```powershell
# Run PowerShell as Admin
cd ".vscode"
.\install-settings.ps1
```
→ Tự động thêm settings vào VS Code

### Option 2: Manual Copy
```
1. Ctrl+Shift+P → "Preferences: Open User Settings (JSON)"
2. Copy nội dung từ .vscode/settings.global.json
3. Save và restart VS Code
```

### Kết quả
- ✅ Memory Stack tự động load trong mọi dự án
- ✅ Claude Code đọc SOUL.md, USER.md, GOVERNANCE.md...
- ✅ Parallel tasks enabled

## Memory Stack v2.1 - Full Context

```
Layer 1: SOUL.md         → Identity & constraints
Layer 2: USER.md         → User preferences
Layer 3: GOVERNANCE.md   → Policy rules
Layer 4: RULES.md        → Operating procedures
Layer 5: COORDINATION.md → Multi-agent workflow
Layer 6: WORKFLOW.md     → Task distribution
Layer 7: CH.md           → Context Hub (API docs)
Layer 8: MEMORY.md       → Project knowledge
Layer 9: memory/         → Daily logs
Layer 10: MemoryOS/     → Full memory OS
Layer 11: .claude/agents/ → Subagents
Layer 12: ULTIMATE_PROMPT.md → Agent Factory
Layer 13: MANIFESTO.md → ∫f(t)dt philosophy
Layer 14: PERFORMANCE_LEDGER.md → CI tracking
```

**Installation:**
```bash
# Context Hub (API Docs)
npm install -g chub-dev

# MemoryOS (Full Memory OS)
bun install -g github:tobi/qmd
cd MemoryOS && memoryos init
```
