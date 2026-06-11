#!/usr/bin/env bash
set -euo pipefail

PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

SERVICE_DIR="/Users/kyle/Knapsack/services/scan-ocr"
BIN_LINK="/Users/kyle/bin/scan-ocr"
PLIST_LINK="/Users/kyle/Library/LaunchAgents/com.kyle.scan-ocr.plist"
LABEL="com.kyle.scan-ocr"
DOMAIN="gui/$(id -u)"

need_file() {
  local path="$1"

  if [[ ! -f "$path" ]]; then
    echo "Missing required file: $path" >&2
    exit 1
  fi
}

replace_with_symlink() {
  local source="$1"
  local link="$2"

  if [[ -e "$link" && ! -L "$link" ]]; then
    echo "Refusing to replace non-symlink: $link" >&2
    exit 1
  fi

  ln -sfn "$source" "$link"
}

bootstrap_agent() {
  local attempt

  for attempt in 1 2 3 4 5; do
    if launchctl bootstrap "$DOMAIN" "$PLIST_LINK"; then
      return 0
    fi

    sleep "$attempt"
  done

  echo "Failed to bootstrap $LABEL after several attempts." >&2
  exit 1
}

wait_for_idle() {
  local waited
  waited=0

  while pgrep -f '^bash /Users/kyle/bin/scan-ocr$' >/dev/null; do
    if (( waited >= 600 )); then
      echo "scan-ocr is still running after 10 minutes; refusing to reload during active OCR." >&2
      exit 1
    fi

    sleep 5
    waited=$((waited + 5))
  done
}

need_file "$SERVICE_DIR/scan-ocr"
need_file "$SERVICE_DIR/com.kyle.scan-ocr.plist"
need_file "$SERVICE_DIR/uninstall.sh"

mkdir -p /Users/kyle/bin /Users/kyle/Library/LaunchAgents /Users/Shared/Scans
mkdir -p "/Users/kyle/Library/Mobile Documents/com~apple~CloudDocs/New Documents/Scans"
mkdir -p /Users/kyle/Library/Logs /Users/kyle/Library/Caches/scan-ocr

chmod +x "$SERVICE_DIR/scan-ocr" "$SERVICE_DIR/install.sh" "$SERVICE_DIR/uninstall.sh"
chmod 644 "$SERVICE_DIR/com.kyle.scan-ocr.plist" "$SERVICE_DIR/README.md"

if ! command -v ocrmypdf >/dev/null 2>&1; then
  echo "ocrmypdf is not installed. Install it with: brew install ocrmypdf" >&2
  exit 1
fi

plutil -lint "$SERVICE_DIR/com.kyle.scan-ocr.plist" >/dev/null

wait_for_idle
launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true

replace_with_symlink "$SERVICE_DIR/scan-ocr" "$BIN_LINK"
replace_with_symlink "$SERVICE_DIR/com.kyle.scan-ocr.plist" "$PLIST_LINK"

bootstrap_agent
launchctl enable "$DOMAIN/$LABEL"
launchctl kickstart "$DOMAIN/$LABEL"

echo "Installed $LABEL"
echo "Status: launchctl print $DOMAIN/$LABEL"
echo "Logs: tail -f /Users/kyle/Library/Logs/scan-ocr.log"
