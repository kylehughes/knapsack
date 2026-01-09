#!/usr/bin/env bash
#===============================================================================
#  set-up-dependencies.sh — Install dependencies via Homebrew bundle
#
#  USAGE:
#    ./scripts/set-up-dependencies.sh
#
#  EXIT CODES:
#    0  success
#    1  homebrew not installed or Brewfile missing
#===============================================================================

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# --- Constants ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Functions ---

command_exists() {
    command -v "$1" &> /dev/null
}

# --- Main ---

log_step "Installing dependencies from Brewfile"

cd "$REPO_ROOT"

if ! command_exists brew; then
    log_error "Homebrew is not installed. Please run: make set-up/homebrew"
    exit 1
fi

if [[ ! -f "Brewfile" ]]; then
    log_error "Brewfile not found in repository root"
    exit 1
fi

echo "Running brew bundle install..."
brew bundle install

echo ""
echo "Checking for missing dependencies..."
brew bundle check || true

log_success "Dependencies setup complete"
