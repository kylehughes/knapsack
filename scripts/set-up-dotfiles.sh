#!/usr/bin/env bash
# Install independent local dotfile copies. Usage: scripts/set-up-dotfiles.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 -B "$SCRIPT_DIR/manage-dotfiles.py" apply
