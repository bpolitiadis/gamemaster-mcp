#!/usr/bin/env python3
"""
CLI and Vercel ASGI entry point for the D&D MCP Server (FastMCP 2.8.0+ compatible).

Vercel's Python runtime loads this module and requires a top-level ``app``
(ASGI). Local CLI / stdio usage continues to call ``main()`` unchanged.
"""

from gamemaster_mcp.main import create_http_app, main

# Vercel (and other ASGI hosts) look for this variable.
app = create_http_app()


def cli_main() -> None:
    """Main CLI entry point."""
    main()


if __name__ == "__main__":
    cli_main()
