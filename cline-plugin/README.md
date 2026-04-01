# NEUTRON EVO OS — Cline Integration

Use NEUTRON EVO OS inside Cline (Claude Line) via MCP (Model Context Protocol).

## Requirements

- [Cline](https://github.com/cline/cline) installed (VS Code extension)
- Python 3.10+
- NEUTRON installed

## Quick Install

```bash
cd /path/to/neutron-evo-os
bash install-cline.sh
```

## What You Get

- **NEUTRON skills as Cline commands** — MCP tools exposed directly in Cline
- **Persistent memory** — Cline sessions share NEUTRON memory across conversations
- **Workflow integration** — Discovery, SPEC, Acceptance available in Cline

## Manual Setup

1. Open VS Code with Cline installed
2. Cline MCP config: `~/.cline/mcp.json` or VS Code settings
3. Add NEUTRON server:

```json
{
  "mcpServers": {
    "NEUTRON-EVO-OS": {
      "command": "python3",
      "args": ["-m", "mcp_server", "--transport", "http", "--port", "3100"],
      "env": {
        "NEUTRON_ROOT": "/path/to/neutron-evo-os"
      }
    }
  }
}
```

4. Reload Cline

## MCP Tools Available in Cline

| Tool | Description |
|------|-------------|
| `neutron_checkpoint` | Write/read session checkpoint |
| `neutron_context` | Audit context files (P0/P1/P2) |
| `neutron_memory` | Memory ops: log, archive, search, dream |
| `neutron_workflow` | Workflow steps: explore, spec, build, ship |
| `neutron_engine` | CI audit, task routing |
| `neutron_audit` | Full system health check |

## MCP Resources

| URI | Description |
|-----|-------------|
| `memory://today` | Today's session memory log |
| `ledger://ci` | Skill CI scores and ratings |
