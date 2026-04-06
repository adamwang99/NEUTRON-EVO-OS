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

from contextvars import ContextVar
from fastapi import FastAPI, Request, Response, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Per-request NEUTRON_ROOT — avoids race conditions across async handlers
_current_neutron_root: ContextVar[str | None] = ContextVar("current_neutron_root", default=None)

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
        version="4.3.1",
        description="Model Context Protocol server over HTTP with API key auth",
    )

    # CORS — use server config (allow_credentials=True requires specific origins, not "*")
    from mcp_server import config as _cfg
    server_cfg = _cfg.get_server_config()
    cors_origins = server_cfg.get("cors_origins", ["*"])
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=False,  # Never True with wildcard origins
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # ── Health check ──────────────────────────────────────────────────────────
    @app.get("/health")
    async def health():
        """Liveness probe."""
        return {"status": "ok", "version": "4.3.1", "server": "NEUTRON-EVO-OS"}

    # ── Ready check ───────────────────────────────────────────────────────────
    @app.get("/ready")
    async def ready():
        """Readiness probe — checks NEUTRON_ROOT is valid. No internal paths leaked."""
        root = os.environ.get("NEUTRON_ROOT", "")
        engine_exists = Path(root, "engine").exists()
        return {
            "status": "ok" if engine_exists else "degraded",
            "engine_found": engine_exists,
        }

    # ── API key validation ────────────────────────────────────────────────────
    @app.get("/keys")
    async def list_keys(x_neutron_api_key: str = Header(...)):
        """List API keys (shows key hints only, not full keys)."""
        # Rate limit check
        rl_allowed, rl_err = auth.check_rate_limit(x_neutron_api_key)
        if not rl_allowed:
            raise HTTPException(status_code=429, detail=rl_err)
        is_auth, _, err = auth.authenticate({"x-neutron-api-key": x_neutron_api_key})
        if not is_auth:
            raise HTTPException(status_code=401, detail=err)
        from mcp_server import config
        return {"keys": config.list_keys()}

    @app.post("/keys")
    async def create_key(
        label: str,
        neutron_root: str | None = None,
        rate_limit: int = Field(default=60, ge=1, le=10000),
        x_neutron_api_key: str = Header(...),
    ):
        """Create a new API key."""
        # Validate neutron_root: must be a real path inside an approved parent tree.
        # Prevents cross-tenant key registration (e.g., key for "/etc" or "../../other-tenant").
        if neutron_root is not None:
            from pathlib import Path
            try:
                nroot = Path(neutron_root).resolve()
            except Exception:
                raise HTTPException(status_code=400, detail="Invalid neutron_root path")
            # Must be a subdirectory of an approved parent
            _SERVER_ROOT = Path(os.environ.get("NEUTRON_ROOT", "/tmp"))
            try:
                nroot.relative_to(_SERVER_ROOT)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail=(
                        f"neutron_root must be inside the NEUTRON server root ({_SERVER_ROOT}). "
                        f"Got: {neutron_root}"
                    ),
                )
        # Rate limit check
        rl_allowed, rl_err = auth.check_rate_limit(x_neutron_api_key)
        if not rl_allowed:
            raise HTTPException(status_code=429, detail=rl_err)
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

        # Set per-request NEUTRON_ROOT via contextvar only — NOT os.environ.
        # ContextVar is copied per async task, so each concurrent request is isolated.
        # os.environ is shared globally — mutating it causes tenant data leaks.
        if api_key != "_anonymous":
            resolved_root = auth.resolve_neutron_root(api_key)
            if resolved_root:
                _current_neutron_root.set(resolved_root)
                # NOTE: We deliberately do NOT set os.environ["NEUTRON_ROOT"] here.
                # Downstream code should call get_current_neutron_root() instead.

        # Handle JSON-RPC request
        from mcp_server import transport as _transport_mod

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

        # Set per-request NEUTRON_ROOT via ContextVar only — no os.environ mutation
        if api_key != "_anonymous":
            resolved_root = auth.resolve_neutron_root(api_key)
            if resolved_root:
                _current_neutron_root.set(resolved_root)

        # Batch size limit: prevent DoS via 100K-item batches
        if len(body) > 100:
            raise HTTPException(
                status_code=413,
                detail="Batch too large: maximum 100 requests per batch",
            )

        from mcp_server import transport as _transport_mod
        results = []
        for req in body:
            # Set ContextVar per-request to ensure clean isolation within the batch.
            # Each iteration gets its own ContextVar copy when we .set() again.
            if api_key != "_anonymous" and resolved_root:
                _current_neutron_root.set(resolved_root)
            try:
                r = _handle_rpc(req)
                if r is not None:
                    results.append(r)
            except Exception as e:
                # Catch per-request errors so one bad request doesn't kill the whole batch
                results.append({
                    "jsonrpc": "2.0",
                    "id": req.get("id"),
                    "error": {"code": -32603, "message": "Internal error processing request"},
                })
        return JSONResponse(content=results)

    return app


# ─── Direct run ────────────────────────────────────────────────────────────────

def get_current_neutron_root() -> str | None:
    """
    Read the per-request NEUTRON_ROOT set by the HTTP transport.

    Use this INSTEAD of os.environ.get("NEUTRON_ROOT") inside request handlers.
    os.environ is shared globally — ContextVar is per-request in async contexts.

    Returns None if called outside an MCP HTTP request (e.g., in stdio mode).
    """
    return _current_neutron_root.get()


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
