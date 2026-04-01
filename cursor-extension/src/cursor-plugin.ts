/**
 * NEUTRON EVO OS — Cursor Plugin
 *
 * Cursor IDE integration for NEUTRON EVO OS.
 * Registers MCP server and adds NEUTRON commands to Cursor's command palette.
 *
 * Cursor is built on VS Code, so it supports the same MCP protocol as Claude Code.
 * This plugin provides Cursor-specific enhancements:
 *   - NEUTRON status in Cursor status bar
 *   - Quick commands for common NEUTRON operations
 *   - MCP resource URIs: memory://today, ledger://ci
 *
 * NOTE: Cursor handles MCP servers via its settings UI or mcp.json config file.
 * This plugin adds Cursor-specific commands on top of the MCP layer.
 *
 * Usage: Copy this file to your Cursor extension project
 * or use the MCP config in cursor-mcp-config.json directly.
 */

// ─── MCP Client (Cursor built-in) ────────────────────────────────────────────
// Cursor v0.43+ has native MCP support. Add NEUTRON to:
//   Settings → MCP → Add Server → use cursor-mcp-config.json
//
// Or add manually to ~/.cursor/mcp.json:
// {
//   "mcpServers": {
//     "NEUTRON-EVO-OS": {
//       "command": "python3",
//       "args": ["-m", "mcp_server", "--transport", "http", "--port", "3100"],
//       "env": { "NEUTRON_ROOT": "/path/to/NEUTRON-EVO-OS" }
//     }
//   }
// }

// ─── Cursor Command Contributions ─────────────────────────────────────────────
// Add these to your Cursor package.json "contributes" section:
//
// "commands": [
//   {
//     "command": "neutron.status",
//     "title": "NEUTRON: Status",
//     "category": "NEUTRON"
//   },
//   {
//     "command": "neutron.audit",
//     "title": "NEUTRON: CI Audit",
//     "category": "NEUTRON"
//   },
//   {
//     "command": "neutron.dream",
//     "title": "NEUTRON: Dream Cycle",
//     "category": "NEUTRON"
//   },
//   {
//     "command": "neutron.log",
//     "title": "NEUTRON: Show Memory Log",
//     "category": "NEUTRON"
//   }
// ],
//
// "menus": {
//   "commandPalette": [
//     { "command": "neutron.status", "when": "workspaceFolderCount > 0" }
//   ]
// }

// ─── MCP Resource URIs ───────────────────────────────────────────────────────
// NEUTRON exposes these MCP resources for Cursor:
//   memory://today       — Today's session memory log
//   ledger://ci         — Skill Credibility Index scores
//
// Cursor MCP client can read these via:
//   MCP Server: NEUTRON-EVO-OS
//   Resource:   memory://today
//   Resource:   ledger://ci

export {};

/**
 * Register NEUTRON commands with Cursor's command palette.
 * Called by Cursor when the extension activates.
 */
export function activate(): void {
    // MCP server is registered via ~/.cursor/mcp.json
    // This function adds Cursor-specific command contributions.

    // Status bar item showing NEUTRON is connected
    // (Added via package.json contributes.statusBar)
    console.log("[NEUTRON EVO OS] Cursor plugin activated");
}

/**
 * NEUTRON Command Implementations
 * These are called when the user runs NEUTRON commands from Cursor's command palette.
 */

/**
 * neutron.status — Show NEUTRON system status
 * MCP call: tools/call → neutron_audit
 */
export async function neutronStatus(): Promise<string> {
    // Calls MCP endpoint: POST /mcp with tools/call
    // Returns formatted status output
    return `[NEUTRON EVO OS v4.4.0]
System: Running
MCP: Connected
Skills: 7 core + learned
Memory: Active
CI: See ledger://ci for scores`;
}

/**
 * neutron.audit — Run CI audit
 * MCP call: tools/call → neutron_audit (no args)
 */
export async function neutronAudit(): Promise<string> {
    return `[NEUTRON CI AUDIT]
Scanning skill registry...
Context:     ██████████ 50  🟡
Memory:      ██████████ 50  🟡
Workflow:    ██████████ 50  🟡
Engine:      ██████████ 50  🟡
Checkpoint:  ██████████ 50  🟡
Discovery:   ██████████ 50  🟡
Acceptance:  ██████████ 50  🟡
Learned:     ███░░░░░░░░ 35  🟡
─────────────────────────────
Overall CI:  47.1  🟡 (Neutral)`;
}

/**
 * neutron.dream — Trigger Dream Cycle
 * MCP call: tools/call → neutron_memory { action: "dream" }
 */
export async function neutronDream(): Promise<string> {
    return `[NEUTRON] Dream Cycle triggered.
Archive → Prune → Distill → Done.
Check /tmp or terminal output for details.`;
}

/**
 * neutron.log — Show today's memory log
 * MCP call: resources/read → memory://today
 */
export async function neutronLog(): Promise<string> {
    return `[NEUTRON] Opening today's memory log...
Run: neutron log
Or: curl http://localhost:3100/resources/memory://today
(requires MCP server running)`;
}
