#!/usr/bin/env bash
#===============================================================================
#  set-up-homebrew.sh — Install Homebrew package manager on macOS
#
#  USAGE:
#    ./scripts/set-up-homebrew.sh
#
#  EXIT CODES:
#    0  success
#    1  installation failed
#===============================================================================

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# --- Constants ---

BREW_INSTALL_URL="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"

# --- Functions ---

command_exists() {
    command -v "$1" &> /dev/null
}

# --- Main ---

log_step "Checking for Homebrew"

if command_exists brew; then
    log_success "Homebrew is already installed"
    echo "  Version: $(brew --version | head -n1)"
    echo ""
    echo "Updating Homebrew..."
    brew update
else
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL $BREW_INSTALL_URL)"

    # Add Homebrew to PATH for this session.
    if [[ -f /opt/homebrew/bin/brew ]]; then
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f /usr/local/bin/brew ]]; then
        eval "$(/usr/local/bin/brew shellenv)"
    fi

    log_success "Homebrew installed"
fi

log_success "Homebrew setup complete"
