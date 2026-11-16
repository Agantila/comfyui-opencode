#!/usr/bin/env bash
# Link this repository into a ComfyUI checkout as a custom node.
#
# Usage: ./install.sh [/path/to/ComfyUI]
# Default target: /home/deniz/ComfyUI
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMFY_DIR="${1:-/home/deniz/ComfyUI}"
TARGET="$COMFY_DIR/custom_nodes/comfyui-opencode"

if [[ ! -d "$COMFY_DIR/custom_nodes" ]]; then
  echo "error: $COMFY_DIR does not look like a ComfyUI checkout" >&2
  exit 1
fi

command -v opencode >/dev/null || {
  echo "error: opencode CLI not found in PATH" >&2
  exit 1
}

if [[ -L "$TARGET" ]]; then
  rm "$TARGET"
elif [[ -e "$TARGET" ]]; then
  echo "error: $TARGET exists and is not a symlink, refusing to overwrite" >&2
  exit 1
fi

ln -s "$REPO_DIR" "$TARGET"
echo "linked $TARGET -> $REPO_DIR"
echo "restart ComfyUI; the node appears under category 'opencode'"
