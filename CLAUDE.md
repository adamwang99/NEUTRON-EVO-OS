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

See `NEUTRON_CONTEXT.md` for the full system context. Additional docs:

- `AI_CONTEXT_MASTER.md` — Project overview
- `ARCHITECTURE.md` — System architecture
- `MEMORY.md` — Project knowledge base
- `engine/` — NEUTRON CLI engine implementation
- `mcp_server/` — MCP server (stdio, SSE, HTTP, WebSocket)
- `skills/` — Claude Code skill definitions
- `hooks/` — Session hooks (session-start, pretool-backup, auto-sync)
- `memory/` — Session logs and discoveries

## Key Conventions

- Follow NEUTRON EVO OS workflow: `/discover → /spec → /build → /verify → /ship`
- Auto-confirm gates controlled by `memory/.auto_confirm.json`
- Hooks run automatically on session start

## Known Issues & Guards

- **Directory boundary**: Observer (`SilentObserver`) and GC are scoped to the active project root. Root path validation rejects parent directories and non-project paths to prevent scanning sibling projects. `stop()` requires the exact root that was used to start.

## Forbidden

- Never commit sensitive files (.env, credentials.json)
- Never skip hooks (--no-verify, --no-gpg-sign)
