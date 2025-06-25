#!/bin/bash
# set-up-dependencies.sh - Install dependencies via Homebrew bundle.
# Usage: ./scripts/set-up-dependencies.sh

set -euo pipefail

# --- Constants ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Functions ---

# Check if a command exists.
command_exists() {
    command -v "$1" &> /dev/null
}

# --- Main ---

echo "Installing dependencies from Brewfile..."

# Ensure we're in the repository root where Brewfile is located.
cd "$REPO_ROOT"

# Check if Homebrew is installed.
if ! command_exists brew; then
    echo "✗ Homebrew is not installed. Please run: make set-up/homebrew"
    exit 1
fi

# Check if Brewfile exists.
if [[ ! -f "Brewfile" ]]; then
    echo "✗ Brewfile not found in repository root."
    exit 1
fi

# Install dependencies.
echo "Running brew bundle install..."
brew bundle install

echo ""
echo "Checking for missing dependencies..."
brew bundle check || true

echo ""
echo "✓ Dependencies setup complete."