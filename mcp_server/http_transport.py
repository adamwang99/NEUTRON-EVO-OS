"""
NEUTRON EVO OS — MCP HTTP Transport
FastAPI JSON-RPC 2.0 server over HTTP.
Usage: uvicorn mcp_server.http_transport:app --port 3100
Or:   python3 -m mcp_server --transport http --port 3100
"""
from __future__ import annotations

import json
import os
import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

# Resolve NEUTRON_ROOT before any other imports
_NEUTRON_ROOT = Path(os.environ.get("NEUTRON_ROOT", str(Path(__file__).parent.parent)))
os.environ["NEUTRON_ROOT"] = str(_NEUTRON_ROOT)
import sys
_root_str = str(_NEUTRON_ROOT)
if _root_str not in sys.path:
    sys.path.insert(0, _root_str)

from mcp_server.transport import handle_request as _handle_rpc
from mcp_server import auth

# ─── Pydantic models ───────────────────────────────────────────────────────────

class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Any = None
    method: str
    params: dict = {}

class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Any = None
    result: Any = None
    error: dict | None = None

# ─── FastAPI app ───────────────────────────────────────────────────────────────

def create_app() -> FastAPI:
    app = FastAPI(
        title="NEUTRON EVO OS — MCP HTTP Server",
        version="4.3.0",
        description="Model Context Protocol server over HTTP with API key auth",
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        """Liveness probe."""
        return {"status": "ok", "version": "4.3.0", "server": "NEUTRON-EVO-OS"}

    # ── Ready check ───────────────────────────────────────────────────────────
    @app.get("/ready")
    async def ready():
        """Readiness probe — checks NEUTRON_ROOT is valid."""
        root = os.environ.get("NEUTRON_ROOT", "")
        engine_exists = Path(root, "engine").exists()
        return {
            "status": "ok" if engine_exists else "degraded",
            "neutron_root": root,
            "engine_found": engine_exists,
        }

    # ── API key validation ────────────────────────────────────────────────────
    @app.get("/keys")
    async def list_keys(x_neutron_api_key: str = Header(...)):
        """List API keys (shows key hints only, not full keys)."""
        is_auth, _, err = auth.authenticate({"x-neutron-api-key": x_neutron_api_key})
        if not is_auth:
            raise HTTPException(status_code=401, detail=err)
        from mcp_server import config
        return {"keys": config.list_keys()}

    @app.post("/keys")
    async def create_key(
        label: str,
        neutron_root: str | None = None,
        rate_limit: int = 60,
        x_neutron_api_key: str = Header(...),
    ):
        """Create a new API key."""
        is_auth, _, err = auth.authenticate({"x-neutron-api-key": x_neutron_api_key})
        if not is_auth:
            raise HTTPException(status_code=401, detail=err)
        from mcp_server import config
        key = config.create_api_key(label, neutron_root, rate_limit)
        return {"api_key": key, "hint": key[-8:], "label": label}

    # ── JSON-RPC endpoint ────────────────────────────────────────────────────
    @app.post("/mcp")
    async def mcp_endpoint(
        body: dict,
        x_neutron_api_key: str = Header(None),
    ):
        """
        JSON-RPC 2.0 endpoint.
        X-NEUTRON-API-Key header required unless accessing public paths.
        """
        # Authenticate
        headers = {"x-neutron-api-key": x_neutron_api_key or ""}
        is_auth, api_key, err = auth.authenticate(headers)
        if not is_auth:
            return JSONResponse(
                status_code=401,
                content={"jsonrpc": "2.0", "id": body.get("id"), "error": {"code": -32603, "message": err}},
            )

        # Set NEUTRON_ROOT for this request from auth
        if api_key != "_anonymous":
            resolved_root = auth.resolve_neutron_root(api_key)
            if resolved_root:
                os.environ["NEUTRON_ROOT"] = resolved_root
                sys.path.insert(0, resolved_root)

        # Handle JSON-RPC request
        # Need to re-import transport with updated NEUTRON_ROOT
        from mcp_server import transport as _transport_mod
        # The transport module reads tools/resources/prompts at call time,
        # so setting env var before calling is sufficient

        try:
            result = _handle_rpc(body)
            if result is None:
                # Notification — no response
                return Response(status_code=204)
            return JSONResponse(content=result)
        except Exception as e:
            return JSONResponse(
                content={
                    "jsonrpc": "2.0",
                    "id": body.get("id"),
                    "error": {"code": -32603, "message": f"Internal error: {e}"},
                }
            )

    # ── Batch endpoint ────────────────────────────────────────────────────────
    @app.post("/mcp/batch")
    async def mcp_batch(
        body: list[dict],
        x_neutron_api_key: str = Header(None),
    ):
        """JSON-RPC 2.0 batch endpoint."""
        headers = {"x-neutron-api-key": x_neutron_api_key or ""}
        is_auth, api_key, err = auth.authenticate(headers)
        if not is_auth:
            return JSONResponse(
                status_code=401,
                content=[{"jsonrpc": "2.0", "id": None, "error": {"code": -32603, "message": err}}],
            )

        if api_key != "_anonymous":
            resolved_root = auth.resolve_neutron_root(api_key)
            if resolved_root:
                os.environ["NEUTRON_ROOT"] = resolved_root

        from mcp_server import transport as _transport_mod
        results = []
        for req in body:
            r = _handle_rpc(req)
            if r is not None:
                results.append(r)
        return JSONResponse(content=results)

    return app


# ─── Direct run ────────────────────────────────────────────────────────────────

def run(port: int = 3100, host: str = "127.0.0.1"):
    """Run HTTP server directly (bypasses uvicorn CLI)."""
    # Ensure config file exists (creates default key if first run)
    from mcp_server import config as _cfg_init
    _cfg_init._load()  # triggers _save() on first run via create_api_key path

    import uvicorn
    app = create_app()
    uvicorn.run(app, host=host, port=port, log_level="info")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="NEUTRON EVO OS — MCP HTTP Server")
    parser.add_argument("--port", type=int, default=3100, help="Port (default 3100)")
    parser.add_argument("--host", default="127.0.0.1", help="Host (default 127.0.0.1)")
    args = parser.parse_args()
    run(port=args.port, host=args.host)
