# Setup ComfyUI

## Install ComfyUI

```bash
git clone https://github.com/comfyanonymous/ComfyUI ~/ComfyUI
cd ~/ComfyUI
pip install -r requirements.txt
```

## Install custom nodes

```bash
bash scripts/setup_comfyui_nodes.sh --comfyui-dir ~/ComfyUI
```

Nodes installed:
- **ComfyUI-Manager** — node management UI
- **ComfyUI_IPAdapter_plus** — IPAdapter for character consistency
- **ComfyUI-Impact-Pack** — face detailer, segmentation
- **ComfyUI-Custom-Scripts** — quality-of-life UI improvements
- **ComfyUI-WanVideoWrapper** — Wan 2.2 I2V support
- **ComfyUI-VideoHelperSuite** — video preview and export

## Download models

```bash
uv run python scripts/download_models.py --profile phase1
```

This downloads:
- Illustrious XL base checkpoint
- SDXL VAE (fp16)
- IPAdapter SDXL models + CLIPVision

## First image

1. Start ComfyUI: `python ~/ComfyUI/main.py --port 8188`
2. Open browser: `http://localhost:8188`
3. Load workflow: drag `workflows/txt2img_base.json` into the ComfyUI canvas
4. Enter a test prompt, click **Queue Prompt**

Target style: anime / cultivation aesthetic. Iterate prompts until satisfied.  
Save 2-3 example prompts as comments in `config/styles/default.yaml`.

## Acceptance

Generate a stylized portrait in <30s per image; visual style matches target.

<!-- TODO: add screenshots to docs/assets/ -->
