"""
Tests for mcp_server/ modules
"""
import pytest
import sys
import json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp_server import transport, tools, resources, prompts


class TestTransport:
    def test_handle_request_initialize(self):
        req = {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}}
        resp = transport.handle_request(req)
        assert resp["jsonrpc"] == "2.0"
        assert resp["id"] == 1
        assert "result" in resp
        assert resp["result"]["protocolVersion"] == "2024-11-05"
        assert resp["result"]["serverInfo"]["name"] == "NEUTRON-EVO-OS"

    def test_handle_request_tools_list(self):
        req = {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}}
        resp = transport.handle_request(req)
        assert "result" in resp
        assert "tools" in resp["result"]
        assert len(resp["result"]["tools"]) >= 6

    def test_handle_request_tools_call(self):
        req = {
            "jsonrpc": "2.0", "id": 3, "method": "tools/call",
            "params": {"name": "neutron_memory", "arguments": {"action": "status", "task": "test"}}
        }
        resp = transport.handle_request(req)
        assert "result" in resp
        assert "content" in resp["result"]

    def test_handle_request_unknown_method(self):
        req = {"jsonrpc": "2.0", "id": 4, "method": "foobar.unknown", "params": {}}
        resp = transport.handle_request(req)
        assert "error" in resp
        assert resp["error"]["code"] == -32601  # Method not found

    def test_handle_request_notification_no_id(self):
        # Notifications have no "id" — should return None (no response sent)
        req = {"jsonrpc": "2.0", "method": "notifications/initialized", "params": {}}
        resp = transport.handle_request(req)
        assert resp is None

    def test_handle_request_resources_list(self):
        req = {"jsonrpc": "2.0", "id": 5, "method": "resources/list", "params": {}}
        resp = transport.handle_request(req)
        assert "result" in resp
        assert "resources" in resp["result"]

    def test_handle_request_prompts_list(self):
        req = {"jsonrpc": "2.0", "id": 6, "method": "prompts/list", "params": {}}
        resp = transport.handle_request(req)
        assert "result" in resp
        assert "prompts" in resp["result"]
        names = [p["name"] for p in resp["result"]["prompts"]]
        assert "neutron_explore" in names
        assert "neutron_spec" in names
        assert "neutron_ship" in names


class TestTools:
    def test_list_tools_returns_11_tools(self):
        result = tools.list_tools()
        assert isinstance(result, list)
        assert len(result) == 11  # checkpoint, context, discovery, spec, memory, workflow, acceptance, engine, audit, auto_confirm, spawn_agent

    def test_all_tools_have_required_fields(self):
        for tool in tools.list_tools():
            assert "name" in tool
            assert "description" in tool
            assert "inputSchema" in tool
            assert tool["name"].startswith("neutron_")

    def test_call_neutron_memory_status(self):
        resp = tools.call_tool("neutron_memory", {"action": "status", "task": "test"})
        assert "content" in resp
        assert isinstance(resp["content"], list)
        assert resp["content"][0]["type"] == "text"

    def test_call_neutron_audit(self):
        resp = tools.call_tool("neutron_audit", {})
        assert "content" in resp

    def test_call_unknown_tool(self):
        resp = tools.call_tool("nonexistent_tool_xyz", {})
        assert "content" in resp
        assert "Unknown tool" in resp["content"][0]["text"]

    def test_call_neutron_workflow_spec_with_criteria(self):
        resp = tools.call_tool(
            "neutron_workflow",
            {"step": "spec", "task": "test", "criteria": ["must work", "must pass"]}
        )
        assert "content" in resp


class TestResources:
    def test_list_resources(self):
        result = resources.list_resources()
        assert isinstance(result, list)
        assert len(result) >= 2
        uris = [r["uri"] for r in result]
        assert "memory://today" in uris
        assert "ledger://ci" in uris

    def test_read_memory_today(self):
        result = resources.read_resource("memory://today")
        assert "contents" in result
        assert result["contents"][0]["uri"] == "memory://today"

    def test_read_ledger_ci(self):
        result = resources.read_resource("ledger://ci")
        assert "contents" in result
        assert result["contents"][0]["uri"] == "ledger://ci"

    def test_read_unknown_resource(self):
        result = resources.read_resource("unknown://resource")
        assert "contents" in result


class TestPrompts:
    def test_list_prompts(self):
        result = prompts.list_prompts()
        assert isinstance(result, list)
        assert len(result) == 6  # explore, discovery, spec, build, acceptance, ship
        names = [p["name"] for p in result]
        assert "neutron_explore" in names
        assert "neutron_spec" in names
        assert "neutron_ship" in names
        assert "neutron_discovery" in names
        assert "neutron_acceptance" in names

    def test_get_prompt_explore(self):
        result = prompts.get_prompt("neutron_explore", {"task": "build a feature"})
        assert "messages" in result
        assert result["messages"][0]["role"] == "user"

    def test_get_prompt_spec(self):
        result = prompts.get_prompt("neutron_spec", {"task": "implement auth"})
        assert "messages" in result
        text = result["messages"][0]["content"]["text"]
        assert "auth" in text or "SPEC.md" in text

    def test_get_prompt_unknown(self):
        result = prompts.get_prompt("nonexistent_prompt", {})
        assert "messages" in result
        assert "Unknown prompt" in result["messages"][0]["content"]["text"]
