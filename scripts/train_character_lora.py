"""Wrapper around kohya_ss sd-scripts to train a character LoRA.

Usage:
    python scripts/train_character_lora.py --config config/characters/my_char.yaml \\
        --refs data/references/characters/my_char/ \\
        --kohya-dir ~/kohya_ss

Requires:
    - kohya_ss installed and its venv activated, OR --kohya-dir pointing to it.
    - accelerate configured for your GPU.
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import yaml

# SDXL LoRA training defaults (rank 32, ~30-60 min on 24GB VRAM)
SDXL_DEFAULTS: dict = {
    "network_dim": 32,
    "network_alpha": 16,
    "max_train_steps": 1200,
    "optimizer_type": "AdamW8bit",
    "learning_rate": 1e-4,
    "text_encoder_lr": 5e-5,
    "train_batch_size": 1,
    "mixed_precision": "fp16",
    "save_precision": "fp16",
    "network_dropout": 0.1,
    "resolution": "1024,1024",
    "enable_bucket": True,
    "min_bucket_reso": 768,
    "max_bucket_reso": 1280,
    "caption_extension": ".txt",
    "shuffle_caption": True,
    "keep_tokens": 1,
    "lr_scheduler": "cosine_with_restarts",
    "lr_warmup_steps": 100,
    "save_every_n_steps": 300,
    "xformers": True,
    "cache_latents": True,
    "cache_latents_to_disk": False,
    "no_half_vae": True,
}

BUCKET_SIZES = [768, 832, 896, 960, 1024, 1088, 1152, 1216, 1280]


def resize_refs(refs_dir: Path, out_dir: Path) -> None:
    """Auto-resize/crop reference images to nearest 1024-bucket size."""
    try:
        from PIL import Image
    except ImportError:
        print("ERROR: Pillow not installed. Run: uv sync", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    images = list(refs_dir.glob("*.png")) + list(refs_dir.glob("*.jpg")) + list(refs_dir.glob("*.jpeg"))
    if not images:
        print(f"ERROR: No images found in {refs_dir}", file=sys.stderr)
        sys.exit(1)

    for img_path in images:
        img = Image.open(img_path).convert("RGB")
        w, h = img.size
        target = min(BUCKET_SIZES, key=lambda b: abs(max(w, h) - b))
        ratio = target / max(w, h)
        nw, nh = int(w * ratio), int(h * ratio)
        img = img.resize((nw, nh), Image.LANCZOS)
        img.save(out_dir / img_path.name)
        # Copy caption if exists
        cap = img_path.with_suffix(".txt")
        if cap.exists():
            shutil.copy(cap, out_dir / cap.name)

    print(f"  Resized {len(images)} images → {out_dir}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Train a character LoRA with kohya_ss")
    parser.add_argument("--config", required=True, type=Path, help="Character YAML config")
    parser.add_argument("--refs", required=True, type=Path, help="Directory of reference images")
    parser.add_argument("--kohya-dir", type=Path, default=Path.home() / "kohya_ss", help="kohya_ss root")
    parser.add_argument("--output-dir", type=Path, default=Path("models/loras/characters"), help="Where to save .safetensors")
    parser.add_argument("--base-model", type=Path, help="Base checkpoint path (overrides config)")
    args = parser.parse_args()

    with open(args.config) as f:
        char = yaml.safe_load(f)

    char_name: str = args.config.stem
    trigger_word: str = char["trigger_word"]
    training_params: dict = {**SDXL_DEFAULTS, **char.get("training_params", {})}

    print(f"Training LoRA for character: {char_name} (trigger: {trigger_word})")

    # Prepare dataset directory in kohya format: {n_repeats}_{trigger} / images
    run_id = datetime.now().strftime("%Y%m%d_%H%M%S")
    dataset_dir = Path(f"/tmp/lora_train_{char_name}_{run_id}")
    repeats = max(1, 1200 // max(1, len(list(args.refs.glob("*.png")) + list(args.refs.glob("*.jpg")))))
    img_dir = dataset_dir / "img" / f"{repeats}_{trigger_word}"
    resize_refs(args.refs, img_dir)

    log_dir = dataset_dir / "log"
    log_dir.mkdir(parents=True, exist_ok=True)

    args.output_dir.mkdir(parents=True, exist_ok=True)
    output_name = char["lora_path"].split("/")[-1].replace(".safetensors", "")

    # Build kohya accelerate command
    train_script = args.kohya_dir / "sd-scripts" / "train_network.py"
    if not train_script.exists():
        train_script = args.kohya_dir / "train_network.py"
    if not train_script.exists():
        print(f"ERROR: train_network.py not found in {args.kohya_dir}", file=sys.stderr)
        sys.exit(1)

    cmd = [
        "accelerate", "launch", "--num_cpu_threads_per_process=1", str(train_script),
        "--pretrained_model_name_or_path", str(args.base_model or ""),
        "--train_data_dir", str(dataset_dir / "img"),
        "--output_dir", str(args.output_dir),
        "--output_name", output_name,
        "--logging_dir", str(log_dir),
        "--network_module", "networks.lora",
        "--v_parameterization",
    ]
    for k, v in training_params.items():
        if isinstance(v, bool):
            if v:
                cmd.append(f"--{k}")
        else:
            cmd.extend([f"--{k}", str(v)])

    # Save training config snapshot next to output
    snapshot_path = args.output_dir / f"{output_name}_train_config.json"
    with open(snapshot_path, "w") as f:
        json.dump({"character": char, "params": training_params, "cmd": cmd}, f, indent=2, default=str)
    print(f"  Training config saved → {snapshot_path}")
    print(f"  Running: {' '.join(cmd[:6])} ...")

    result = subprocess.run(cmd, check=False)
    if result.returncode != 0:
        print(f"ERROR: Training failed (exit {result.returncode})", file=sys.stderr)
        sys.exit(result.returncode)

    print(f"\nLoRA saved → {args.output_dir / (output_name + '.safetensors')}")
    print("Next: validate with txt2img_lora.json workflow using 10 test prompts.")


if __name__ == "__main__":
    main()
