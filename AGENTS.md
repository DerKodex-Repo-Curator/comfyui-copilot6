# AGENTS.md

## Cursor Cloud specific instructions

ComfyUI-Copilot is a **ComfyUI custom node plugin**. All agent logic runs locally inside ComfyUI; **no developer-hosted API key or Render.com backend is required**.

### Self-hosted mode (default)

- Configure **Chat LLM** and optional **Workflow LLM** in Copilot Settings (gear icon).
- Supported: OpenAI (`https://api.openai.com/v1`), Anthropic models via OpenRouter (`https://openrouter.ai/api/v1`), LMStudio (`http://localhost:1234/v1`), or any OpenAI-compatible endpoint.
- Env fallbacks in repo root `.env`: `CC_OPENAI_API_KEY`, `CC_OPENAI_BASE_URL`, `WORKFLOW_LLM_API_KEY`, `WORKFLOW_LLM_BASE_URL`, `WORKFLOW_LLM_MODEL`.

### Local features (no external Copilot server)

| Feature | Route / module |
|---------|----------------|
| Chat + workflow generation | `POST /api/chat/invoke` → `backend/service/mcp_client.py` + `local_workflow_tools.py` |
| Load workflow to canvas | `POST /api/chat/get_optimized_workflow` → `backend/controller/workflow_api.py` |
| Missing node info | `POST /api/chat/get_node_info_by_types` (uses local `/object_info`) |
| Debug / rewrite canvas | `POST /api/debug-agent`, rewrite agent handoff |
| Model download | `POST /api/download-model` (ModelScope SDK) |

Workflow generation uses **installed nodes** (`/object_info`) and **local model files** (`folder_paths`).

### ComfyUI host setup

See prior setup notes: clone ComfyUI, symlink this repo into `custom_nodes/ComfyUI-Copilot`, `pip install -r requirements.txt`, `cd ui && npm run build`, start ComfyUI with `--cpu` on GPU-less VMs.

### Commands

| Task | Command |
|------|---------|
| Python deps | `pip3 install -r requirements.txt` |
| UI deps | `cd ui && npm install` |
| UI build | `cd ui && npm run build` |
