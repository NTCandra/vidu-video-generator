"""Batch image generation from a scenes list."""
from __future__ import annotations

import json
import os
import random
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from video_pipeline.imagegen.comfy_client import ComfyClient

load_dotenv()
console = Console()

# Defaults applied when pipeline.yaml / scene data don't specify these fields.
_GENERATION_DEFAULTS: dict[str, Any] = {
    "checkpoint": "Illustrious-XL-v0.1.safetensors",
    "vae": "sdxl_vae_fp16.safetensors",
    "steps": 30,
    "cfg": 6.5,
    "sampler": "dpmpp_2m",
    "scheduler": "karras",
    "width": 1024,
    "height": 1024,
}


def _load_workflow_template(workflow_name: str) -> dict[str, Any]:
    """Load an API-format workflow from ``workflows/api/<name>.json``."""
    name = workflow_name if workflow_name.endswith(".json") else f"{workflow_name}.json"
    path = Path("workflows/api") / name
    if not path.exists():
        raise FileNotFoundError(
            f"API workflow template not found: {path}\n"
            "Templates live in workflows/api/ and use {{param}} placeholders."
        )
    with open(path) as f:
        return json.load(f)


def _load_style(style_name: str = "default") -> dict[str, Any]:
    """Load a style preset from ``config/styles/<name>.yaml``."""
    path = Path("config/styles") / f"{style_name}.yaml"
    if not path.exists():
        return {}
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _load_pipeline_config() -> dict[str, Any]:
    """Load imagegen section from config/pipeline.yaml, returning {} on missing file."""
    path = Path("config/pipeline.yaml")
    if not path.exists():
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return data.get("imagegen", {})


def _build_prompts(scene: dict[str, Any], style: dict[str, Any]) -> tuple[str, str]:
    """Combine scene ``image_prompt_en`` with style tags and mood additions."""
    base = scene.get("image_prompt_en", "")
    mood = scene.get("mood", "default")

    pos_tags: list[str] = style.get("positive_tags", [])
    neg_tags: list[str] = style.get("negative_tags", [])
    mood_data = style.get("mood_prompt_additions", {})
    mood_entry = mood_data.get(mood, mood_data.get("default", {}))

    positive = ", ".join(filter(None, [base] + pos_tags + mood_entry.get("positive", [])))
    negative = ", ".join(filter(None, neg_tags + mood_entry.get("negative", [])))
    return positive, negative


def generate_batch(
    scenes: list[dict[str, Any]],
    workflow_name: str,
    output_dir: Path,
    *,
    comfyui_url: str | None = None,
    timeout: int = 300,
    style_name: str = "default",
) -> dict[str, Path]:
    """Generate one image per scene. Returns ``{scene_id: image_path}``.

    Requests are serialized — ComfyUI processes one prompt at a time.
    A rich progress bar tracks per-scene status.
    """
    url = comfyui_url or os.getenv("COMFYUI_URL", "http://127.0.0.1:8188")
    pipeline_cfg = _load_pipeline_config()
    workflow_template = _load_workflow_template(workflow_name)
    style = _load_style(style_name)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Build generation defaults: code defaults < pipeline.yaml < call-site
    gen_defaults: dict[str, Any] = {
        **_GENERATION_DEFAULTS,
        "checkpoint": pipeline_cfg.get("checkpoint", _GENERATION_DEFAULTS["checkpoint"]),
        "vae": pipeline_cfg.get("vae", _GENERATION_DEFAULTS["vae"]),
        "steps": pipeline_cfg.get("steps", _GENERATION_DEFAULTS["steps"]),
        "cfg": pipeline_cfg.get("cfg", _GENERATION_DEFAULTS["cfg"]),
        "sampler": pipeline_cfg.get("sampler", _GENERATION_DEFAULTS["sampler"]),
        "scheduler": pipeline_cfg.get("scheduler", _GENERATION_DEFAULTS["scheduler"]),
        "width": pipeline_cfg.get("width", _GENERATION_DEFAULTS["width"]),
        "height": pipeline_cfg.get("height", _GENERATION_DEFAULTS["height"]),
    }

    results: dict[str, Path] = {}

    with ComfyClient(url) as client:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=console,
        ) as progress:
            task = progress.add_task("Starting…", total=len(scenes))

            for i, scene in enumerate(scenes, 1):
                scene_id: str = scene["id"]
                progress.update(task, description=f"[{i}/{len(scenes)}] {scene_id} — generating")

                positive, negative = _build_prompts(scene, style)
                seed = scene.get("seed", random.randint(0, 2**32 - 1))

                params: dict[str, Any] = {
                    **gen_defaults,
                    "positive_prompt": positive,
                    "negative_prompt": negative,
                    "seed": seed,
                }

                workflow = client.inject_params(workflow_template, params)
                scene_out = output_dir / scene_id
                scene_out.mkdir(parents=True, exist_ok=True)

                prompt_id = client.submit_workflow(workflow)
                progress.update(task, description=f"[{i}/{len(scenes)}] {scene_id} — waiting")
                client.wait_for_completion(prompt_id, timeout=timeout)

                images = client.download_outputs(prompt_id, scene_out)
                if images:
                    results[scene_id] = images[0]
                    progress.update(task, advance=1, description=f"[{i}/{len(scenes)}] {scene_id} ✓")
                else:
                    console.print(f"[yellow]⚠ No images returned for scene {scene_id}[/yellow]")
                    progress.update(task, advance=1)

    return results
