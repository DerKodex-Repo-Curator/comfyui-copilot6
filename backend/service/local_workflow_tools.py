# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""Local replacements for hosted MCP workflow tools."""

from __future__ import annotations

import json
from typing import Any, Dict

try:
    from agents.tool import function_tool
except Exception:
    raise ImportError("openai-agents is required for ComfyUI-Copilot local tools")

from ..utils.logger import log
from .local_workflow_generator import generate_workflow_from_requirement
from .local_workflow_store import workflow_store
from .workflow_rewrite_tools import get_node_infos, search_node_local


def _tool_response(answer: str, data: Any = None) -> str:
    payload = {"answer": answer, "data": data or []}
    return json.dumps({"text": json.dumps(payload, ensure_ascii=False)}, ensure_ascii=False)


@function_tool
async def recall_workflow(query: str) -> str:
    """Search previously generated local workflows similar to the user's request."""
    try:
        matches = workflow_store.search(query, limit=3)
        if not matches:
            return _tool_response(
                "No matching workflows in the local library yet. Use gen_workflow to create one.",
                [],
            )
        return _tool_response(f"Found {len(matches)} similar locally stored workflow(s).", matches)
    except Exception as exc:
        log.error(f"recall_workflow failed: {exc}")
        return _tool_response(f"Local workflow search failed: {exc}", [])


@function_tool
async def gen_workflow(description: str) -> str:
    """Generate a new ComfyUI workflow using installed nodes and local models."""
    try:
        metadata = await generate_workflow_from_requirement(description)
        return _tool_response("Generated a new workflow from your requirements.", [metadata])
    except Exception as exc:
        log.error(f"gen_workflow failed: {exc}")
        return _tool_response(f"Workflow generation failed: {exc}", [])


LOCAL_AGENT_TOOLS = [
    recall_workflow,
    gen_workflow,
    search_node_local,
    get_node_infos,
]
