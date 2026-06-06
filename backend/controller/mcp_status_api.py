# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""Health/discovery routes for the built-in MCP server."""

from __future__ import annotations

import server
from aiohttp import web

from ..service.mcp_server_runner import ensure_mcp_server_running, get_mcp_server_url
from ..utils.logger import log


@server.PromptServer.instance.routes.get("/api/mcp/status")
async def mcp_status(_request: web.Request) -> web.Response:
    try:
        ensure_mcp_server_running(wait_seconds=2)
        return web.json_response(
            {
                "success": True,
                "url": get_mcp_server_url(),
                "transport": "sse",
            }
        )
    except Exception as exc:
        log.error(f"MCP status check failed: {exc}")
        return web.json_response({"success": False, "message": str(exc)}, status=503)
