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
if [[ -z "$PIPER" ]]; then
  PIPER="$ROOT/.venv/bin/piper"
fi
if [[ ! -x "$PIPER" ]]; then
  echo "ERROR: piper binary missing after pip install piper-tts"
  exit 1
fi
"$PIPER" --help | head -1

MODEL="$ROOT/data/voices/hi_IN-pratham-medium.onnx"
test -f "$MODEL" || { echo "missing voice model"; exit 1; }

printf '%s' "शिव जी की कहानी परीक्षण।" > /tmp/ci_tts_in.txt
"$PIPER" --model "$MODEL" --input_file /tmp/ci_tts_in.txt --output_file /tmp/ci_tts_test.wav --length_scale 1.2
test -f /tmp/ci_tts_test.wav
echo "CI TTS stack OK"