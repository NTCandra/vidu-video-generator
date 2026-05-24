# vidu-video-generator

Automated pipeline to produce Vietnamese-language anime/stylized narrative videos for YouTube, targeting cultivation (tu tiên) / fantasy / romance genres with consistent recurring characters.

**Hardware requirements:** 96 GB RAM + 24 GB VRAM (NVIDIA), Linux or WSL2.  
**Target cadence:** 1 video / 2-3 days, mostly automated.

## Architecture

```
Story (.md) → LLM scene breakdown → ComfyUI image gen → Vietnamese TTS
           → Ken Burns / I2V animation → MoviePy assembly → output.mp4
```

## Quick start

See [docs/00_quickstart.md](docs/00_quickstart.md).

## Tech stack

| Component | Choice |
|-----------|--------|
| Orchestrator | Python 3.11+, Typer (`vpipe` CLI) |
| LLM | Qwen 2.5 32B via Ollama (or Anthropic API) |
| Image gen | ComfyUI + Illustrious XL |
| Character consistency | LoRA per main character + IPAdapter |
| Video / I2V | Wan 2.2 |
| Lip-sync | LivePortrait |
| TTS (Vietnamese) | GPT-SoVITS / F5-TTS |
| Assembly | MoviePy + FFmpeg |

## Setup

```bash
# Install dependencies (requires uv)
uv sync

# Copy and fill in secrets
cp .env.example .env

# Verify CLI
uv run vpipe --help
```

## Development

Dev tools (ruff, mypy, pytest) are installed automatically by `uv sync`.

```bash
uv run ruff check src/
uv run mypy src/
uv run pytest
```
