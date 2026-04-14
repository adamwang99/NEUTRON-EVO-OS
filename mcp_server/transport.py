"""
NEUTRON EVO OS — MCP Server: stdio JSON-RPC 2.0 Transport
Handles inbound requests from Claude Code MCP client.
"""
from __future__ import annotations

import json
import sys
from typing import Any


def read_request() -> dict | None:
    """Read one JSON-RPC request from stdin. Blocks until line available."""
    try:
        line = sys.stdin.readline()
    except UnicodeDecodeError:
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Encoding error"}}
    if not line:
        return None
    try:
        return json.loads(line.strip())
    except (json.JSONDecodeError, ValueError):
        return {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "Parse error"}}


def write_response(data: dict):
    """Write JSON-RPC response or notification to stdout (flush immediately)."""
    sys.stdout.write(json.dumps(data) + "\n")
    sys.stdout.flush()


def handle_request(req: dict) -> dict | None:
    """
    Route MCP request to appropriate handler.
    Returns a response dict, or None for notifications (no id).
    """
    from mcp_server import tools, resources, prompts

    method = req.get("method", "")
    req_id = req.get("id")
    params = req.get("params") or {}

    if not isinstance(params, dict):
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {"code": -32602, "message": f"Invalid params type: {type(params).__name__}, expected object"},
        }

    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": {
                "protocolVersion": "2024-11-05",
                "capabilities": {"tools": {}, "resources": {}, "prompts": {}},
                "serverInfo": {"name": "NEUTRON-EVO-OS", "version": "4.3.2"},
            },
        }

    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"tools": tools.list_tools()}}

    if method == "tools/call":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": tools.call_tool(params.get("name", ""), params.get("arguments", {})),
        }

    if method == "resources/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"resources": resources.list_resources()}}

    if method == "resources/read":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": resources.read_resource(params.get("uri", "")),
        }

    if method == "prompts/list":
        return {"jsonrpc": "2.0", "id": req_id, "result": {"prompts": prompts.list_prompts()}}

    if method == "prompts/get":
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": prompts.get_prompt(params.get("name", ""), params.get("arguments", {})),
        }

    # Notifications (no id) are just acked silently
    if req_id is None:
        return None

    return {
        "jsonrpc": "2.0",
        "id": req_id,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main():
    """Run MCP server on stdio — read request, handle, write response, repeat."""
    while True:
        req = read_request()
        if req is None:
            break
        resp = handle_request(req)
        if resp is not None:
            write_response(resp)
