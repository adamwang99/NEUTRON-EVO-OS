# AI Context Master — NEUTRON EVO OS

> Internal project: NEUTRON EVO OS source code itself.

## Stack

- Python (CLI engine, MCP server)
- Node.js (integrations)
- Claude API

## Commands

- MCP server: `python3 -m mcp_server --transport http --port 3100`
- Run tests: `pytest`
- GC cleanup: `neutron gc --pycache --tests --data-json`

## Local Docs

See `NEUTRON_CONTEXT.md` for the full system context.
- `memory/LEARNED.md` — **Bug fixes & patterns: read before starting any fix**
- `memory/archived/AUDIT_NOTES_2026-04-06.md` — Full system audit (scores, CI state, remaining issues)
- `engine/` — NEUTRON CLI engine implementation
- `mcp_server/` — MCP server (stdio, SSE, HTTP, WebSocket)
- `skills/` — Claude Code skill definitions
- `hooks/` — Session hooks (session-start.sh, gc_lightweight.py)
- `memory/` — Session logs, cookbooks, shipments, learned

## Key Conventions

- Follow NEUTRON EVO OS workflow: `explore → discovery → spec → build → verify → acceptance → ship`
- Auto-confirm gates: `memory/.auto_confirm.json` controls bypass
- SessionStart: runs GC, injects LEARNED bugs + cookbook patterns, triggers Dream Cycle (12h debounce)
- CI routing: keyword-based (65%) + CI signal (35%) — see `engine/expert_skill_router.py`
- Swarm agents: `spawn_parallel(unit_configs)` in `mcp_server/tools.py` — true N-agent parallel
- Distill: ship step writes `memory/pending/LEARNED_pending.md` for review

## Known Issues

- **Dream Cycle AI**: Requires `ANTHROPIC_API_KEY` env var (Anthropic format). Non-AI phases work without it.
- **Directory boundary**: Read/Glob/Grep blocked outside project root via `pretool-guard.sh`. Observer and GC scoped to project root only.
- **PreLoadMemory**: Not a valid hook. Use SessionStart instead.
- Legacy docs archived to `memory/archived/`.

## Forbidden

- Never commit sensitive files (.env, credentials.json)
- Never skip hooks (--no-verify, --no-gpg-sign)
