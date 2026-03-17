# AI Context Master

This project uses AI Context Master for enhanced AI assistance.

## CRITICAL: File Backup Rule

**Before ANY file edit, agent MUST:**
1. Copy original file to `.backup/` folder first
2. THEN edit the file

Example: Before editing `src/api.ts` → First copy to `.backup/src/api.ts.backup`

## Context Files

For full context, read these files (in order):
- **SOUL.md** - AI identity and constraints
- **USER.md** - User preferences
- **GOVERNANCE.md** - Policy rules
- **RULES.md** - Operating procedures (includes backup rules)
- **DESIGN_SYSTEM.md** - Design standards
- **WORKFLOW.md** - Task workflow
- **START.md** - Quick start guide

For full documentation, see README.md

## Setup for New Projects

Run `apply-context.bat` (Windows) or `apply-context.sh` (Mac/Linux) to copy this context to any project.
