# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""Built-in FastMCP server exposing ComfyUI-aware tools for Copilot agents."""

from __future__ import annotations

from typing import List, Optional

from fastmcp import FastMCP
from fastmcp.server.dependencies import get_http_request

from ..utils.logger import log
from . import comfyui_mcp_toolkit as toolkit

MCP_SERVER_NAME = "ComfyUI-Copilot"
MCP_SSE_PATH = "/mcp"

mcp = FastMCP(MCP_SERVER_NAME)


def _bind_request_context() -> None:
    try:
        request = get_http_request()
        toolkit.bind_session_from_headers(dict(request.headers))
    except Exception as exc:
        log.debug(f"MCP request context bind skipped: {exc}")


@mcp.tool
async def recall_workflow(query: str) -> str:
    """Search locally stored generated workflows similar to the user's request."""
    _bind_request_context()
    return await toolkit.tool_recall_workflow(query)


@mcp.tool
async def gen_workflow(description: str) -> str:
    """Generate a ComfyUI workflow using installed nodes and local model files."""
    _bind_request_context()
    return await toolkit.tool_gen_workflow(description)


@mcp.tool
async def search_node(
    node_class: str = "",
    keywords: Optional[List[str]] = None,
    limit: int = 10,
) -> str:
    """Search installed ComfyUI nodes (class names, categories, input params)."""
    _bind_request_context()
    return await toolkit.tool_search_node_local(node_class, keywords, limit)


@mcp.tool
async def get_node_infos(node_class_list: List[str]) -> str:
    """Fetch detailed schemas for up to ~5 installed node class types."""
    _bind_request_context()
    return await toolkit.tool_get_node_infos(node_class_list)


@mcp.tool
async def get_current_workflow() -> str:
    """Return the current canvas workflow JSON for this session."""
    _bind_request_context()
    return await toolkit.tool_get_current_workflow()


@mcp.tool
async def list_available_models() -> str:
    """List model filenames available in local ComfyUI model folders."""
    _bind_request_context()
    return await toolkit.tool_list_available_models()


@mcp.tool
async def list_installed_node_types(limit: int = 200) -> str:
    """List installed ComfyUI node class_type names from /object_info."""
    _bind_request_context()
    return await toolkit.tool_list_installed_node_types(limit)
