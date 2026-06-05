#!/usr/bin/env bash
set -euo pipefail

PATH="/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

LABEL="com.kyle.scan-ocr"
DOMAIN="gui/$(id -u)"
BIN_LINK="/Users/kyle/bin/scan-ocr"
PLIST_LINK="/Users/kyle/Library/LaunchAgents/com.kyle.scan-ocr.plist"

launchctl bootout "$DOMAIN/$LABEL" >/dev/null 2>&1 || true

for path in "$BIN_LINK" "$PLIST_LINK"; do
  if [[ -L "$path" ]]; then
    rm -f "$path"
  elif [[ -e "$path" ]]; then
    echo "Leaving non-symlink in place: $path" >&2
  fi
done

echo "Uninstalled $LABEL"
echo "Logs and scanned files were left in place."
