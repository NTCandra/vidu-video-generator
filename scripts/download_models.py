"""Download required model weights from Hugging Face Hub.

Usage:
    python scripts/download_models.py --profile phase1
    python scripts/download_models.py --profile phase1 --comfyui-dir "C:/Users/Admin/AppData/Roaming/ComfyUI"
    python scripts/download_models.py --profile phase6
    python scripts/download_models.py --profile all
"""

from __future__ import annotations

import argparse
import hashlib
import sys
from pathlib import Path

try:
    from huggingface_hub import hf_hub_download, snapshot_download
except ImportError:
    print("ERROR: huggingface_hub not installed. Run: uv sync", file=sys.stderr)
    sys.exit(1)

DEFAULT_COMFYUI_ROOT = Path.home() / "ComfyUI"

PROFILE_ENTRIES: dict[str, list[dict]] = {
    "phase1": [
        {
            "description": "Illustrious XL base checkpoint",
            "repo_id": "OnomaAIResearch/Illustrious-xl-early-release-v0",
            "filename": "Illustrious-XL-v0.1.safetensors",
            "dest_rel": "models/checkpoints",
        },
        {
            "description": "SDXL VAE fp16",
            "repo_id": "madebyollin/sdxl-vae-fp16-fix",
            "filename": "diffusion_pytorch_model.safetensors",
            "dest_rel": "models/vae",
            "rename_to": "sdxl_vae_fp16.safetensors",
        },
        {
            "description": "IPAdapter SDXL (ViT-H)",
            "repo_id": "h94/IP-Adapter",
            "filename": "sdxl_models/ip-adapter_sdxl_vit-h.safetensors",
            "dest_rel": "models/ipadapter",
        },
        {
            "description": "CLIPVision ViT-H (for IPAdapter)",
            "repo_id": "h94/IP-Adapter",
            "filename": "models/image_encoder/model.safetensors",
            "dest_rel": "models/clip_vision",
            "rename_to": "clip_vision_vit_h.safetensors",
        },
    ],
    "phase6": [
        {
            "description": "Wan 2.2 I2V weights",
            "repo_id": "Wan-AI/Wan2.2-I2V-14B-480P",
            "dest_rel": "models/wan",
            "snapshot": True,
        },
    ],
}
PROFILE_ENTRIES["all"] = [item for items in PROFILE_ENTRIES.values() for item in items]


def sha256(path: Path, chunk: int = 1 << 20) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        while data := f.read(chunk):
            h.update(data)
    return h.hexdigest()


def download_file(entry: dict, comfyui_root: Path) -> None:
    dest_dir = comfyui_root / entry["dest_rel"]
    dest_dir.mkdir(parents=True, exist_ok=True)

    if entry.get("snapshot"):
        print(f"  [snapshot] {entry['description']} → {dest_dir}")
        snapshot_download(repo_id=entry["repo_id"], local_dir=str(dest_dir))
        return

    filename: str = entry["filename"]
    rename_to: str = entry.get("rename_to", Path(filename).name)
    final_path = dest_dir / rename_to

    if final_path.exists():
        print(f"  [skip] {rename_to} already exists")
        return

    print(f"  [download] {entry['description']}")
    downloaded = hf_hub_download(
        repo_id=entry["repo_id"],
        filename=filename,
        local_dir=str(dest_dir),
    )
    src = Path(downloaded)
    if src != final_path:
        src.rename(final_path)

    digest = sha256(final_path)
    print(f"  [ok] {final_path.name}  sha256={digest[:16]}…")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download pipeline model weights")
    parser.add_argument(
        "--profile",
        choices=list(PROFILE_ENTRIES.keys()),
        default="phase1",
        help="Which set of models to download (default: phase1)",
    )
    parser.add_argument(
        "--comfyui-dir",
        type=Path,
        default=DEFAULT_COMFYUI_ROOT,
        help=f"Path to ComfyUI root directory (default: {DEFAULT_COMFYUI_ROOT})",
    )
    args = parser.parse_args()

    comfyui_root: Path = args.comfyui_dir
    entries = PROFILE_ENTRIES[args.profile]
    print(f"Downloading profile '{args.profile}' ({len(entries)} items) into {comfyui_root}\n")

    for entry in entries:
        download_file(entry, comfyui_root)

    print("\nAll downloads complete.")


if __name__ == "__main__":
    main()
