# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""Start the built-in ComfyUI Copilot MCP server on a local port (non-blocking)."""

from __future__ import annotations

import asyncio
import logging
import os
import threading
from typing import Optional

import httpx

from .comfyui_mcp_server import MCP_SSE_PATH, mcp

logger = logging.getLogger(__name__)

_mcp_thread: Optional[threading.Thread] = None
_mcp_port: Optional[int] = None
_mcp_start_lock = threading.Lock()


def get_mcp_port(comfyui_port: int = 8188) -> int:
    override = os.environ.get("COPILOT_MCP_PORT")
    if override:
        try:
            return int(override)
        except ValueError:
            pass
    return comfyui_port + 1


def get_mcp_server_url(comfyui_port: int = 8188) -> str:
    path = MCP_SSE_PATH if MCP_SSE_PATH.startswith("/") else f"/{MCP_SSE_PATH}"
    return f"http://127.0.0.1:{get_mcp_port(comfyui_port)}{path}"


def _run_mcp_server(port: int) -> None:
    async def _serve() -> None:
        await mcp.run_http_async(
            transport="sse",
            host="127.0.0.1",
            port=port,
            path=MCP_SSE_PATH,
        )

    try:
        asyncio.run(_serve())
    except Exception as exc:
        logger.error("ComfyUI Copilot MCP server stopped: %s", exc)


def _start_mcp_thread(port: int) -> None:
    global _mcp_thread, _mcp_port
    with _mcp_start_lock:
        if _mcp_thread is not None and _mcp_thread.is_alive():
            return
        _mcp_port = port
        _mcp_thread = threading.Thread(
            target=_run_mcp_server,
            args=(port,),
            name="comfyui-copilot-mcp",
            daemon=True,
        )
        _mcp_thread.start()
        logger.info("ComfyUI Copilot MCP server starting on http://127.0.0.1:%s/mcp", port)


def ensure_mcp_server_running(comfyui_port: int = 8188, wait_seconds: float = 0) -> str:
    """Start MCP in a background thread. Optional short wait for health (default: no wait)."""
    port = get_mcp_port(comfyui_port)
    _start_mcp_thread(port)
    url = get_mcp_server_url(comfyui_port)

    if wait_seconds <= 0:
        return url

    attempts = max(1, int(wait_seconds / 0.25))
    for _ in range(attempts):
        try:
            with httpx.Client(timeout=1.0) as client:
                client.get(url)
            return url
        except Exception:
            pass
        import time

        time.sleep(0.25)

    logger.warning("MCP server may still be starting at %s", url)
    return url
