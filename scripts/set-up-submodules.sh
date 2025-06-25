#!/bin/bash
# set-up-submodules.sh - Initialize and update git submodules.
# Usage: ./scripts/set-up-submodules.sh

set -euo pipefail

# --- Constants ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# --- Main ---

echo "Setting up git submodules..."

# Ensure we're in the repository root.
cd "$REPO_ROOT"

# Check if we're in a git repository.
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo "✗ Not in a git repository."
    exit 1
fi

# Initialize and update submodules.
echo "Initializing submodules..."
git submodule init

echo ""
echo "Updating submodules..."
git submodule update --recursive

# Show submodule status.
echo ""
echo "Submodule status:"
git submodule status

echo ""
echo "✓ Submodules setup complete."