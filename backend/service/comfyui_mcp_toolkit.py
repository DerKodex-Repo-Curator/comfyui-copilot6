# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""Shared ComfyUI MCP tool implementations (used by FastMCP server and fallbacks)."""

from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from ..utils.comfy_gateway import get_object_info
from ..utils.logger import log
from ..utils.request_context import set_session_id, restore_request_context_from_session
from .local_workflow_generator import build_environment_context, generate_workflow_from_requirement
from .local_workflow_store import workflow_store
from ..dao.workflow_table import get_workflow_data


def bind_session_from_headers(headers: Optional[Dict[str, str]] = None) -> None:
    if not headers:
        return
    normalized = {k.lower(): v for k, v in headers.items()}
    session_id = normalized.get("x-session-id")
    if session_id:
        restore_request_context_from_session(session_id)


def mcp_tool_payload(answer: str, data: Any = None) -> str:
    """Format expected by mcp_client tool-result parser."""
    inner = {"answer": answer, "data": data or []}
    return json.dumps({"text": json.dumps(inner, ensure_ascii=False)}, ensure_ascii=False)


async def tool_recall_workflow(query: str) -> str:
    matches = workflow_store.search(query, limit=3)
    if not matches:
        return mcp_tool_payload(
            "No matching workflows in the local library yet. Use gen_workflow to create one.",
            [],
        )
    return mcp_tool_payload(f"Found {len(matches)} similar locally stored workflow(s).", matches)


async def tool_gen_workflow(description: str) -> str:
    metadata = await generate_workflow_from_requirement(description)
    return mcp_tool_payload("Generated a new workflow from your requirements.", [metadata])


async def tool_get_current_workflow() -> str:
    from ..utils.request_context import get_session_id

    session_id = get_session_id()
    if not session_id:
        return json.dumps({"error": "No session_id found in context"})
    workflow_data = get_workflow_data(session_id)
    if not workflow_data:
        return json.dumps({"error": "No workflow data found for this session"})
    return json.dumps(workflow_data, ensure_ascii=False)


async def tool_search_node_local(
    node_class: str = "",
    keywords: Optional[List[str]] = None,
    limit: int = 10,
) -> str:
    from .workflow_rewrite_tools import search_node_local

    payload = json.dumps(
        {"node_class": node_class, "keywords": keywords or [], "limit": limit},
        ensure_ascii=False,
    )
    return await search_node_local.on_invoke_tool(None, payload)


async def tool_get_node_infos(node_class_list: List[str]) -> str:
    from .workflow_rewrite_tools import get_node_infos

    payload = json.dumps({"node_class_list": node_class_list}, ensure_ascii=False)
    return await get_node_infos.on_invoke_tool(None, payload)


async def tool_list_available_models() -> str:
    return build_environment_context()


async def tool_list_installed_node_types(limit: int = 200) -> str:
    object_info = await get_object_info()
    names = sorted(object_info.keys())[: max(1, min(limit, 500))]
    return json.dumps({"total": len(object_info), "sample": names}, ensure_ascii=False)
