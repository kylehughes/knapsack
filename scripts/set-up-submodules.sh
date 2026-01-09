#!/usr/bin/env bash
#===============================================================================
#  set-up-submodules.sh — Initialize and update git submodules
#
#  USAGE:
#    ./scripts/set-up-submodules.sh
#
#  EXIT CODES:
#    0  success
#    1  not in a git repository
#===============================================================================

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# --- Constants ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Main ---

log_step "Setting up git submodules"

cd "$REPO_ROOT"

if ! git rev-parse --git-dir > /dev/null 2>&1; then
    log_error "Not in a git repository"
    exit 1
fi

echo "Initializing submodules..."
git submodule init

echo ""
echo "Updating submodules..."
git submodule update --recursive

echo ""
echo "Submodule status:"
git submodule status

log_success "Submodules setup complete"
