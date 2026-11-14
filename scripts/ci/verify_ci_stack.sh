#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"
# shellcheck disable=SC1091
source .venv/bin/activate

pip install -q onnxruntime piper-tts

command -v ffmpeg
python -c "import onnxruntime; print('onnxruntime ok')"

PIPER="$(command -v piper || true)"
if [[ -z "$PIPER" && -x "$ROOT/.local/piper/piper" ]]; then
  PIPER="$ROOT/.local/piper/piper"
fi
if [[ -z "$PIPER" && -x "$ROOT/.venv/bin/piper" ]]; then
  PIPER="$ROOT/.venv/bin/piper"
fi
if [[ -z "$PIPER" ]]; then
  echo "ERROR: piper binary missing — install_cloud_deps should fetch rhasspy/piper"
  exit 1
fi
"$PIPER" --help | head -1 || "$PIPER" 2>&1 | head -1 || true

MODEL="$ROOT/data/voices/hi_IN-pratham-medium.onnx"
test -f "$MODEL" || { echo "missing voice model"; exit 1; }

printf '%s' "शिव जी की कहानी परीक्षण।" > /tmp/ci_tts_in.txt
"$PIPER" --model "$MODEL" --input_file /tmp/ci_tts_in.txt --output_file /tmp/ci_tts_test.wav --length_scale 1.2
test -f /tmp/ci_tts_test.wav
echo "CI TTS stack OK"