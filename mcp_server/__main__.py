"""Entry point: python -m mcp_server [--transport stdio|http] [--port N]"""
from __future__ import annotations

import argparse
import sys


def main():
    parser = argparse.ArgumentParser(prog="python -m mcp_server")
    parser.add_argument(
        "--transport", "-t",
        choices=["stdio", "http"],
        default="stdio",
        help="Transport mode: stdio (Claude Code) or http (Cursor/Cline/custom clients). Default: stdio",
    )
    parser.add_argument(
        "--port", "-p",
        type=int, default=3100,
        help="Port for HTTP transport. Default: 3100",
    )
    parser.add_argument(
        "--host",
        default="127.0.0.1",
        help="Host for HTTP transport. Default: 127.0.0.1",
    )
    args = parser.parse_args()

    if args.transport == "stdio":
        from mcp_server.transport import main as stdio_main
        sys.exit(stdio_main())
    elif args.transport == "http":
        from mcp_server.http_transport import run
        run(port=args.port, host=args.host)


if __name__ == "__main__":
    main()
