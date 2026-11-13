#!/usr/bin/env bash
# Install macOS LaunchAgents for 3 PM generate+upload and 6 PM queue (no GitHub runner required).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
LABEL_PREFIX="com.youtube.muskathya"
PLIST_DIR="$HOME/Library/LaunchAgents"

chmod +x "$ROOT/scripts/run_daily_automation.sh" "$ROOT/scripts/run_upload_queue.sh" "$ROOT/scripts/preflight_automation.sh"

install_plist() {
  local name=$1
  local hour=$2
  local minute=$3
  local script=$4
  local plist="$PLIST_DIR/${LABEL_PREFIX}.${name}.plist"

  cat > "$plist" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL_PREFIX}.${name}</string>
  <key>WorkingDirectory</key>
  <string>${ROOT}</string>
  <key>ProgramArguments</key>
  <array>
    <string>/bin/bash</string>
    <string>${script}</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>${hour}</integer>
    <key>Minute</key>
    <integer>${minute}</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${ROOT}/logs/launchd_${name}.log</string>
  <key>StandardErrorPath</key>
  <string>${ROOT}/logs/launchd_${name}.err</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>PATH</key>
    <string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin</string>
  </dict>
</dict>
</plist>
EOF

  launchctl bootout "gui/$(id -u)/${LABEL_PREFIX}.${name}" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$plist"
  launchctl enable "gui/$(id -u)/${LABEL_PREFIX}.${name}"
  echo "Installed $plist"
}

mkdir -p "$PLIST_DIR" "$ROOT/logs"

# Default times from .env if present
GEN_H=15
GEN_M=0
PUB_H=18
PUB_M=0
if [[ -f "$ROOT/.env" ]]; then
  # shellcheck disable=SC1091
  source "$ROOT/.env"
  GEN_H="${PIPELINE_DAILY_RUN_HOUR:-15}"
  GEN_M="${PIPELINE_DAILY_RUN_MINUTE:-0}"
  PUB_H="${PUBLISH_HOUR:-18}"
  PUB_M="${PUBLISH_MINUTE:-0}"
fi

install_plist "daily-generate" "$GEN_H" "$GEN_M" "$ROOT/scripts/run_daily_automation.sh"
install_plist "upload-queue" "$PUB_H" "$PUB_M" "$ROOT/scripts/run_upload_queue.sh"

echo ""
echo "Done. Mac will run generate+upload at ${GEN_H}:$(printf '%02d' "$GEN_M") and upload-queue at ${PUB_H}:$(printf '%02d' "$PUB_M") IST."
echo "Logs: $ROOT/logs/launchd_*.log"
echo "Optional daemon (always-on): python -m app.main scheduler"
