#!/usr/bin/env bash
# Installs required ComfyUI custom nodes into ComfyUI/custom_nodes/.
# Idempotent: skips repos that are already cloned.
# Usage: ./scripts/setup_comfyui_nodes.sh [--comfyui-dir /path/to/ComfyUI]

set -euo pipefail

COMFYUI_DIR="${COMFYUI_DIR:-$HOME/ComfyUI}"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --comfyui-dir) COMFYUI_DIR="$2"; shift 2;;
    *) echo "Unknown argument: $1"; exit 1;;
  esac
done

NODES_DIR="$COMFYUI_DIR/custom_nodes"

if [[ ! -d "$COMFYUI_DIR" ]]; then
  echo "ERROR: ComfyUI not found at $COMFYUI_DIR"
  echo "Install ComfyUI first: https://github.com/comfyanonymous/ComfyUI"
  exit 1
fi

mkdir -p "$NODES_DIR"

clone_or_skip() {
  local repo="$1"
  local name
  name=$(basename "$repo" .git)
  if [[ -d "$NODES_DIR/$name" ]]; then
    echo "  [skip] $name already exists"
  else
    echo "  [clone] $name"
    git clone --depth 1 "$repo" "$NODES_DIR/$name"
  fi
}

echo "Installing ComfyUI custom nodes into: $NODES_DIR"
echo ""

clone_or_skip "https://github.com/ltdrdata/ComfyUI-Manager.git"
clone_or_skip "https://github.com/cubiq/ComfyUI_IPAdapter_plus.git"
clone_or_skip "https://github.com/ltdrdata/ComfyUI-Impact-Pack.git"
clone_or_skip "https://github.com/pythongosssss/ComfyUI-Custom-Scripts.git"
clone_or_skip "https://github.com/jags111/efficiency-nodes-comfyui.git"
clone_or_skip "https://github.com/florestefano1975/comfyui-portrait-master.git"
clone_or_skip "https://github.com/Fannovel16/comfyui_controlnet_aux.git"
clone_or_skip "https://github.com/kijai/ComfyUI-WanVideoWrapper.git"
clone_or_skip "https://github.com/Kosinkadink/ComfyUI-VideoHelperSuite.git"

echo ""
echo "Done. Restart ComfyUI to load the new nodes."
echo "Then open ComfyUI Manager to install any missing Python dependencies."
