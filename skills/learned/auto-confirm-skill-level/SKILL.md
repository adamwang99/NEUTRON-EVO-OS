---
name: auto-confirm-skill-level
type: learned
version: 0.1.0
CI: 35
dependencies: []
last_dream: 2026-04-01
---

## Learned Skill: Auto-Confirm Enforcement at SKILL.md Level

### Pattern
When implementing an auto-confirm/config system, the configuration exists but the AI doesn't read it because it's only checked at the Python execution layer (skill_execution.run()), not at the SKILL.md layer that Claude Code reads directly. Claude Code reads SKILL.md files to understand what to do — it never calls skill_execution.run() during normal chat. Fix: add FIRST STEP sections to SKILL.md files that tell the AI to check the config file before presenting gates.

### When to Apply
- Implementing any "auto" or "skip" mode for a workflow gate
- Adding configuration that should control AI behavior
- Making sure a Python config layer is actually enforced by the AI itself

### Example
**Problem:** Auto-confirm config exists at `memory/.auto_confirm.json`, Python code checks it, but Claude Code ignores it because it doesn't run the Python code during chat.

**Fix applied:**
```markdown
## ⚡ FIRST STEP: Check Auto-Confirm Status
**BEFORE doing anything else**, check if auto-confirm is enabled:
1. Read memory/.auto_confirm.json
2. If {"enabled": true}: → skip the gate
3. Only present gate UI if auto-confirm is FALSE
```

Also update CLAUDE.md (loaded first) with the same check.

### Notes
Realized during Phase 6 (2026-04-01) when user complained auto-confirm wasn't working despite being enabled.
Root cause: AI reads CLAUDE.md + SKILL.md for guidance, not Python code.
Solution: embed the check in the docs the AI actually reads.
