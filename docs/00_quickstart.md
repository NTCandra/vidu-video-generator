# Quickstart

## Prerequisites

- Linux or Windows WSL2
- NVIDIA GPU with 24 GB VRAM
- Python 3.11+
- [uv](https://docs.astral.sh/uv/) package manager
- [Ollama](https://ollama.ai) (for local LLM)
- [ComfyUI](https://github.com/comfyanonymous/ComfyUI) (for image generation)

## 1. Clone and install

```bash
git clone <your-repo-url> vidu-video-generator
cd vidu-video-generator
uv sync
cp .env.example .env
```

Edit `.env` with your service URLs.

## 2. Verify CLI

```bash
uv run vpipe --help
```

You should see 6 commands: `scenes`, `images`, `voice`, `animate`, `assemble`, `run`.

## 3. Set up ComfyUI (Phase 1)

```bash
# Install custom nodes (idempotent)
bash scripts/setup_comfyui_nodes.sh --comfyui-dir ~/ComfyUI

# Download models
uv run python scripts/download_models.py --profile phase1 --comfyui-dir ~/ComfyUI
```

See [01_setup_comfyui.md](01_setup_comfyui.md) for detailed instructions.

## 4. Full pipeline (after all phases complete)

```bash
uv run vpipe run --story data/stories/my_story.md --out data/output/
```

## Phase roadmap

| Week | Phases | Deliverable |
|------|--------|-------------|
| 1 | 0 → 2 | Programmatic image generation |
| 2 | 3 → 4 | Character LoRA + voice profiles |
| 3 | 5 → 7 | First end-to-end pilot video |
| 4 | 8 → 9 | Lip-sync + orchestrator |
