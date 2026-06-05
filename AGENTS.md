# AGENTS.md

## Cursor Cloud specific instructions

ComfyUI-Copilot is a **ComfyUI custom node plugin**, not a standalone app. Full end-to-end development requires ComfyUI as the host runtime.

### Architecture

| Component | Location | Role |
|-----------|----------|------|
| Python plugin | repo root (`backend/`, `__init__.py`) | Registers `/api/*` routes on ComfyUI's `PromptServer` |
| React UI | `ui/` | Built to `dist/copilot_web/`; served at `/copilot_web/` |
| Host app | ComfyUI (external) | Must be installed separately and load this repo via `custom_nodes/` |

### One-time ComfyUI host setup (outside this repo)

ComfyUI is not vendored in this repository. For cloud VMs without GPU:

```bash
git clone --depth 1 https://github.com/comfyanonymous/ComfyUI.git ~/ComfyUI
mkdir -p ~/ComfyUI/custom_nodes
ln -sfn /workspace ~/ComfyUI/custom_nodes/ComfyUI-Copilot

# CPU PyTorch (required on GPU-less VMs)
pip3 install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu
pip3 install torchsde
grep -v '^torch' ~/ComfyUI/requirements.txt | grep -v '^torchvision' | grep -v '^torchaudio' | pip3 install -r /dev/stdin
```

Ensure `$HOME/.local/bin` is on `PATH` for scripts installed by pip.

### Build UI before running in ComfyUI

ComfyUI will log an error if `dist/copilot_web/` is missing. From repo root:

```bash
cd ui && npm run build
```

### Starting ComfyUI with the plugin

```bash
export PATH="$HOME/.local/bin:$PATH"
cd ~/ComfyUI
python3 main.py --cpu --listen 127.0.0.1 --port 8188
```

Use `--cpu` on machines without CUDA. On GPU hosts, omit `--cpu`.

Verify the plugin loaded in startup logs (`Import times for custom nodes: ... ComfyUI-Copilot`) and that `http://127.0.0.1:8188/copilot_web/input.js` returns HTTP 200.

### UI development (hot reload)

Run ComfyUI on port 8188 first, then in a separate terminal:

```bash
cd ui && npm run dev
```

Vite proxies ComfyUI frontend scripts from `http://127.0.0.1:8188`.

### Lint / test / build commands

| Task | Command | Notes |
|------|---------|-------|
| UI lint | `cd ui && npm run lint` | Requires `@typescript-eslint/eslint-plugin` and `@typescript-eslint/parser` (referenced in `.eslintrc.cjs` but not listed in `package.json`; install locally if lint fails) |
| UI typecheck | `cd ui && npx tsc --noEmit` | Some `.ts` files contain JSX and may error; primary check is `npm run build` |
| UI build | `cd ui && npm run build` | Output: `dist/copilot_web/` |
| Python deps | `pip3 install -r requirements.txt` | From repo root |
| Python tests | None configured | `pytest` is listed in `requirements.txt` but no `tests/` directory exists |

### Gotchas

- **SQLAlchemy version tension**: this plugin pins `sqlalchemy>=1.4.0,<2.0` while current ComfyUI requires `SQLAlchemy>=2.0.0`. ComfyUI's install may upgrade SQLAlchemy; watch for plugin DB issues.
- **LLM API key**: Agent features need an OpenAI-compatible API key configured in Copilot Settings (or env vars `CC_OPENAI_API_KEY`, `CC_OPENAI_BASE_URL`). Hosted Copilot API endpoints are suspended per README.
- **Lint noise**: `npm run lint` reports many Prettier formatting issues in the existing codebase; this is pre-existing, not an environment problem.
