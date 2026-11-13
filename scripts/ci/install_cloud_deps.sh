#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VOICE_DIR="$ROOT/data/voices"
mkdir -p "$VOICE_DIR"

sudo apt-get update -qq
sudo apt-get install -y ffmpeg libespeak-ng1

if [[ ! -f "$VOICE_DIR/hi_IN-pratham-medium.onnx" ]]; then
  curl -fsSL -o "$VOICE_DIR/hi_IN-pratham-medium.onnx" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx"
fi
if [[ ! -f "$VOICE_DIR/hi_IN-pratham-medium.onnx.json" ]]; then
  curl -fsSL -o "$VOICE_DIR/hi_IN-pratham-medium.onnx.json" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json"
fi
