#!/bin/bash
# set-up-homebrew.sh - Install Homebrew package manager on macOS.
# Usage: ./scripts/set-up-homebrew.sh

set -euo pipefail

# --- Constants ---

BREW_INSTALL_URL="https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh"

# --- Functions ---

# Check if a command exists.
command_exists() {
    command -v "$1" &> /dev/null
}

# --- Main ---

echo "Checking for Homebrew..."

if command_exists brew; then
    echo "✓ Homebrew is already installed."
    echo "  Version: $(brew --version | head -n1)"
    echo ""
    echo "Updating Homebrew..."
    brew update
else
    echo "Installing Homebrew..."
    /bin/bash -c "$(curl -fsSL $BREW_INSTALL_URL)"
    
    # Add Homebrew to PATH for this session.
    if [[ -f /opt/homebrew/bin/brew ]]; then
        # Apple Silicon Mac.
        eval "$(/opt/homebrew/bin/brew shellenv)"
    elif [[ -f /usr/local/bin/brew ]]; then
        # Intel Mac.
        eval "$(/usr/local/bin/brew shellenv)"
    fi
    
    echo "✓ Homebrew installed successfully."
fi

echo "✓ Homebrew setup complete."