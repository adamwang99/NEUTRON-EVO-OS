# NEUTRON EVO OS — Cursor IDE Integration

Use NEUTRON EVO OS inside Cursor IDE via MCP (Model Context Protocol).

## Requirements

- [Cursor](https://cursor.sh) installed
- Python 3.10+ with `pip install fastapi uvicorn`
- NEUTRON installed: `bash install.sh cli` or `bash install.sh full`

## Quick Install

```bash
cd /path/to/neutron-evo-os
bash install-cursor.sh
```

This detects your Cursor installation and configures the MCP server automatically.

## What You Get

- **NEUTRON skills as Cursor commands** — Run `Cmd+K` → type NEUTRON commands
- **MCP Resources** — Access memory logs, CI ledger directly from Cursor
- **Workflow prompts** — `Cmd+K` → NEUTRON prompts (explore, spec, build, ship)
- **Persistent session** — MCP keeps NEUTRON state across Cursor sessions

## Manual Setup

If `install-cursor.sh` doesn't work:

1. Find Cursor's MCP config location:
   ```bash
   ls ~/.cursor/mcp.json 2>/dev/null || ls ~/Library/Application\ Support/Cursor/User/settings/mcp.json 2>/dev/null
   ```

2. Add this to your Cursor MCP settings:
   ```json
   {
     "NEUTRON-EVO-OS": {
       "command": "python3",
       "args": ["-m", "mcp_server", "--transport", "http", "--port", "3100"]
     }
   }
   ```

3. Restart Cursor

## Troubleshooting

**NEUTRON not responding in Cursor?**
```bash
# Check if MCP server is running
curl http://localhost:3100/health

# Start manually
python3 -m mcp_server --transport http --port 3100
```

**Wrong NEUTRON_ROOT?**
```bash
export NEUTRON_ROOT=/path/to/neutron-evo-os
python3 -m mcp_server --transport http --port 3100
```
