#!/bin/sh
# Install a daily morning launchd job to import Proof Pix CSVs from the inbox folder.
# Default: 7:00 AM local time. Override with PROOFPIX_SCHEDULE_HOUR=8

set -e

BACKEND_DIR="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="${PYTHON_BIN:-python3}"
HOUR="${PROOFPIX_SCHEDULE_HOUR:-7}"
LABEL="com.hivecommand.proofpix-inbox"
PLIST_PATH="$HOME/Library/LaunchAgents/${LABEL}.plist"
LOG_DIR="$BACKEND_DIR/logs"
LOG_PATH="$LOG_DIR/proofpix-inbox.log"

mkdir -p "$LOG_DIR"

cat > "$PLIST_PATH" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key>
  <string>${LABEL}</string>
  <key>ProgramArguments</key>
  <array>
    <string>${PYTHON_BIN}</string>
    <string>${BACKEND_DIR}/sync_proofpix_inbox.py</string>
  </array>
  <key>WorkingDirectory</key>
  <string>${BACKEND_DIR}</string>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key>
    <integer>${HOUR}</integer>
    <key>Minute</key>
    <integer>0</integer>
  </dict>
  <key>StandardOutPath</key>
  <string>${LOG_PATH}</string>
  <key>StandardErrorPath</key>
  <string>${LOG_PATH}</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/${LABEL}" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl enable "gui/$(id -u)/${LABEL}"

echo "Installed ${LABEL} for ${HOUR}:00 daily."
echo "Inbox sync log: ${LOG_PATH}"
echo "Test now with: cd ${BACKEND_DIR} && ${PYTHON_BIN} sync_proofpix_inbox.py"
