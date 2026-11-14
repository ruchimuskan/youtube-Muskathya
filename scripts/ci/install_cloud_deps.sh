#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
VOICE_DIR="$ROOT/data/voices"
PIPER_DIR="$ROOT/.local/piper"
mkdir -p "$VOICE_DIR" "$PIPER_DIR"

sudo apt-get update -qq
sudo apt-get install -y ffmpeg libespeak-ng1 espeak-ng libsndfile1 wget

if [[ ! -x "$PIPER_DIR/piper" ]]; then
  ARCH="$(uname -m)"
  case "$ARCH" in
    x86_64)
      URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_x86_64.tar.gz"
      ;;
    aarch64|arm64)
      URL="https://github.com/rhasspy/piper/releases/download/2023.11.14-2/piper_linux_aarch64.tar.gz"
      ;;
    *)
      echo "WARN: unknown arch $ARCH — will rely on pip piper-tts"
      URL=""
      ;;
  esac
  if [[ -n "$URL" ]]; then
    tmp="$(mktemp -d)"
    curl -fsSL "$URL" | tar -xzf - -C "$tmp"
    if [[ -x "$tmp/piper/piper" ]]; then
      cp -a "$tmp/piper/"* "$PIPER_DIR/"
    elif [[ -x "$tmp/piper" ]]; then
      cp "$tmp/piper" "$PIPER_DIR/piper"
    fi
    chmod +x "$PIPER_DIR/piper" 2>/dev/null || true
    rm -rf "$tmp"
  fi
fi

if [[ -x "$PIPER_DIR/piper" ]]; then
  if [[ -n "${GITHUB_PATH:-}" ]]; then
    echo "$PIPER_DIR" >> "$GITHUB_PATH"
  fi
  export PATH="$PIPER_DIR:$PATH"
fi

if [[ ! -f "$VOICE_DIR/hi_IN-pratham-medium.onnx" ]]; then
  curl -fsSL -o "$VOICE_DIR/hi_IN-pratham-medium.onnx" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx"
fi
if [[ ! -f "$VOICE_DIR/hi_IN-pratham-medium.onnx.json" ]]; then
  curl -fsSL -o "$VOICE_DIR/hi_IN-pratham-medium.onnx.json" \
    "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/hi/hi_IN/pratham/medium/hi_IN-pratham-medium.onnx.json"
fi
