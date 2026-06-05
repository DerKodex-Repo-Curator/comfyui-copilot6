# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""OpenAI Agents function_tool wrappers; MCP server uses comfyui_mcp_toolkit directly."""

from __future__ import annotations

from . import comfyui_mcp_toolkit as toolkit
from .comfyui_mcp_toolkit import mcp_tool_payload
from .workflow_rewrite_tools import search_node_local, get_node_infos

try:
    from agents.tool import function_tool
except Exception:
    raise ImportError("openai-agents is required for ComfyUI-Copilot local tools")


@function_tool
async def recall_workflow(query: str) -> str:
    return await toolkit.tool_recall_workflow(query)


@function_tool
async def gen_workflow(description: str) -> str:
    return await toolkit.tool_gen_workflow(description)


LOCAL_AGENT_TOOLS = [recall_workflow, gen_workflow, search_node_local, get_node_infos]
