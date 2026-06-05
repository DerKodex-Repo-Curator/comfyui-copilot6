# Copyright (C) 2025 AIDC-AI
# Licensed under the MIT License.

"""Generate ComfyUI API-format workflows using the user's LLM and local environment."""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Set

import folder_paths
from openai import OpenAI
from pydantic import BaseModel, Field

from ..utils.comfy_gateway import get_object_info
from ..utils.key_utils import workflow_config_adapt
from ..utils.logger import log
from ..utils.request_context import get_config
from ..utils.globals import WORKFLOW_MODEL_NAME, OPENAI_BASE_URL, OPENAI_API_KEY
from .local_workflow_store import workflow_store


class GeneratedWorkflowPayload(BaseModel):
    name: str = Field(description="Short workflow title")
    description: str = Field(description="What this workflow does")
    workflow_data: str = Field(description="ComfyUI API-format workflow JSON string")


def _list_model_files(folder_name: str, limit: int = 30) -> List[str]:
    try:
        return folder_paths.get_filename_list(folder_name)[:limit]
    except Exception:
        return []


def build_environment_context() -> str:
    """Summarize locally installed models and node categories for the LLM."""
    model_folders = [
        "checkpoints",
        "loras",
        "vae",
        "clip",
        "unet",
        "diffusion_models",
        "text_encoders",
        "controlnet",
        "upscale_models",
        "embeddings",
    ]
    models: Dict[str, List[str]] = {}
    for folder in model_folders:
        files = _list_model_files(folder)
        if files:
            models[folder] = files

    return json.dumps({"available_models": models}, ensure_ascii=False)


async def build_node_context(required_classes: Optional[List[str]] = None) -> str:
    object_info = await get_object_info()
    if not object_info:
        return json.dumps({"error": "Could not read /object_info from ComfyUI"})

    if required_classes:
        subset = {k: object_info[k] for k in required_classes if k in object_info}
        return json.dumps(subset, ensure_ascii=False)

    # Compact catalog: class -> category + required input names
    catalog: Dict[str, Dict[str, Any]] = {}
    for class_name, meta in object_info.items():
        category = meta.get("category", "")
        inputs = meta.get("input", {})
        required = list((inputs.get("required") or {}).keys())[:8]
        optional = list((inputs.get("optional") or {}).keys())[:4]
        catalog[class_name] = {
            "category": category,
            "required_inputs": required,
            "optional_inputs": optional,
        }
    return json.dumps(catalog, ensure_ascii=False)


def _resolve_llm_client():
    config = workflow_config_adapt(get_config() or {})
    base_url = (
        config.get("openai_base_url")
        or config.get("workflow_llm_base_url")
        or OPENAI_BASE_URL
        or "https://api.openai.com/v1"
    )
    api_key = (
        config.get("openai_api_key")
        or config.get("workflow_llm_api_key")
        or OPENAI_API_KEY
        or ""
    )
    model = (
        config.get("workflow_llm_model")
        or config.get("model_select")
        or WORKFLOW_MODEL_NAME
    )
    if not api_key and not base_url.lower().find("localhost") >= 0:
        raise ValueError(
            "No LLM API key configured. Set your OpenAI/Anthropic-compatible API key in Copilot Settings."
        )
    return OpenAI(base_url=base_url, api_key=api_key or "local"), model


def validate_workflow_api(workflow_api: Dict[str, Any], installed_nodes: Set[str]) -> List[str]:
    missing: List[str] = []
    for node_id, node in workflow_api.items():
        if not isinstance(node, dict):
            continue
        class_type = node.get("class_type")
        if class_type and class_type not in installed_nodes:
            missing.append(class_type)
    return sorted(set(missing))


async def generate_workflow_from_requirement(requirement: str) -> Dict[str, Any]:
    """Generate a workflow, store it locally, and return public metadata."""
    requirement = (requirement or "").strip()
    if not requirement:
        raise ValueError("Workflow requirement is empty")

    client, model = _resolve_llm_client()
    node_context = await build_node_context()
    env_context = build_environment_context()

    system_prompt = """You are a ComfyUI workflow architect. Build a runnable ComfyUI API-format workflow.

Rules:
- Output ONLY valid ComfyUI API JSON in workflow_data (keys are string node ids like "1", "2").
- Each node must include class_type and inputs.
- Use ONLY node class_type values that exist in the provided installed_nodes catalog.
- Prefer model filenames from available_models when loading checkpoints/loras/vae/unet.
- Ensure required inputs are connected or set to sensible literals.
- Include SaveImage or PreviewImage so the user gets visible output.
- Keep workflows focused and minimal (typically 5-15 nodes).
"""

    user_prompt = f"""User requirement:
{requirement}

Installed nodes (class_type catalog):
{node_context}

Locally available model files:
{env_context}
"""

    completion = client.chat.completions.parse(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        max_tokens=8192,
        temperature=0.2,
        response_format=GeneratedWorkflowPayload,
    )

    parsed = completion.choices[0].message.parsed
    if not parsed or not parsed.workflow_data:
        raise ValueError("LLM returned empty workflow")

    workflow_api = json.loads(parsed.workflow_data)
    object_info = await get_object_info()
    missing = validate_workflow_api(workflow_api, set(object_info.keys()))
    if missing:
        log.warning(f"Generated workflow references missing nodes: {missing}")

    workflow_id = workflow_store.add(
        workflow_api=workflow_api,
        name=parsed.name or "AI Generated Workflow",
        description=parsed.description or requirement,
        source="AI Generated",
    )

    metadata = workflow_store.get(workflow_id)
    assert metadata is not None
    return workflow_store._public_metadata(metadata)


async def optimize_stored_workflow(workflow_id: int, user_prompt: str) -> Dict[str, Any]:
    """Return stored workflow for canvas load, optionally refined for the user prompt."""
    stored = workflow_store.get(workflow_id)
    if not stored:
        raise ValueError(f"Workflow {workflow_id} not found")

    workflow_api = stored["workflow_api"]
    object_info = await get_object_info()

    # Light refinement: if user prompt differs from description, ask LLM to tweak params only
    if user_prompt and user_prompt.strip() and user_prompt.strip() != stored.get("description", ""):
        try:
            client, model = _resolve_llm_client()
            completion = client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": "Adjust the ComfyUI API workflow JSON for the user's request. Return ONLY JSON.",
                    },
                    {
                        "role": "user",
                        "content": json.dumps(
                            {
                                "request": user_prompt,
                                "workflow": workflow_api,
                                "installed_nodes": list(object_info.keys())[:500],
                            },
                            ensure_ascii=False,
                        ),
                    },
                ],
                max_tokens=8192,
                temperature=0.1,
            )
            text = completion.choices[0].message.content or ""
            start = text.find("{")
            end = text.rfind("}")
            if start >= 0 and end > start:
                workflow_api = json.loads(text[start : end + 1])
        except Exception as exc:
            log.warning(f"Workflow optimization skipped: {exc}")

    return {
        "workflow": workflow_api,
        "optimized_params": [],
    }
