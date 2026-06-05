# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""Local API routes replacing the hosted ComfyUI-Copilot server."""

from __future__ import annotations

import json
from typing import Any, Dict, List

import server
from aiohttp import web

from ..service.local_workflow_generator import optimize_stored_workflow
from ..utils.comfy_gateway import get_object_info
from ..utils.logger import log
from ..controller.conversation_api import get_llm_config_from_headers
from ..utils.globals import apply_llm_env_defaults
from ..utils.request_context import set_request_context


@server.PromptServer.instance.routes.post("/api/chat/get_optimized_workflow")
async def get_optimized_workflow(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        workflow_id = int(body.get("workflow_id"))
        prompt = body.get("prompt") or ""

        config = apply_llm_env_defaults(get_llm_config_from_headers(request))
        set_request_context(body.get("session_id"), None, config)

        data = await optimize_stored_workflow(workflow_id, prompt)
        return web.json_response({"success": True, "data": data})
    except Exception as exc:
        log.error(f"get_optimized_workflow failed: {exc}")
        return web.json_response({"success": False, "message": str(exc)}, status=400)


@server.PromptServer.instance.routes.post("/api/chat/get_node_info_by_types")
async def get_node_info_by_types(request: web.Request) -> web.Response:
    try:
        body = await request.json()
        node_types: List[str] = body.get("node_types") or []
        object_info = await get_object_info()

        results: List[Dict[str, Any]] = []
        for node_type in node_types:
            if node_type in object_info:
                meta = object_info[node_type]
                github_url = _guess_repository_url(node_type, meta)
                results.append(
                    {
                        "name": node_type,
                        "github_url": github_url,
                        "display_name": meta.get("display_name") or meta.get("name") or node_type,
                        "category": meta.get("category"),
                        "installed": True,
                    }
                )
            else:
                results.append(
                    {
                        "name": node_type,
                        "github_url": "",
                        "display_name": node_type,
                        "category": None,
                        "installed": False,
                    }
                )

        return web.json_response({"success": True, "data": results})
    except Exception as exc:
        log.error(f"get_node_info_by_types failed: {exc}")
        return web.json_response({"success": False, "message": str(exc)}, status=400)


@server.PromptServer.instance.routes.post("/api/param_debug/generate_sd_prompts")
async def generate_sd_prompts_local(request: web.Request) -> web.Response:
    """Local fallback for hosted prompt expansion."""
    try:
        from openai import OpenAI
        from ..utils.globals import OPENAI_API_KEY, OPENAI_BASE_URL, WORKFLOW_MODEL_NAME

        body = await request.json()
        text = (body.get("text") or "").strip()
        config = apply_llm_env_defaults(get_llm_config_from_headers(request))

        client = OpenAI(
            base_url=config.get("openai_base_url") or OPENAI_BASE_URL or "https://api.openai.com/v1",
            api_key=config.get("openai_api_key") or OPENAI_API_KEY or "",
        )
        model = config.get("model_select") or WORKFLOW_MODEL_NAME
        completion = client.chat.completions.create(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": "Generate 5 diverse Stable Diffusion prompt variations. Return JSON array of strings only.",
                },
                {"role": "user", "content": text},
            ],
            max_tokens=1024,
            temperature=0.8,
        )
        content = completion.choices[0].message.content or "[]"
        start = content.find("[")
        end = content.rfind("]")
        prompts = json.loads(content[start : end + 1]) if start >= 0 else [text]
        return web.json_response({"success": True, "data": prompts})
    except Exception as exc:
        log.error(f"generate_sd_prompts_local failed: {exc}")
        return web.json_response({"success": False, "message": str(exc)}, status=400)


def _guess_repository_url(node_type: str, meta: Dict[str, Any]) -> str:
    python_module = meta.get("python_module") if isinstance(meta, dict) else None
    if isinstance(python_module, str) and python_module.startswith("custom_nodes."):
        parts = python_module.split(".")
        if len(parts) >= 2:
            pack = parts[1]
            return f"https://github.com/search?q={pack}+comfyui&type=repositories"
    return f"https://www.google.com/search?q={node_type.replace(' ', '+')}+comfyui+custom+node"
