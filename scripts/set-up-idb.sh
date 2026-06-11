#!/usr/bin/env bash
#===============================================================================
#  set-up-idb.sh — Install and verify Facebook idb tooling
#
#  USAGE:
#    ./scripts/set-up-idb.sh
#
#  EXIT CODES:
#    0  success
#    1  missing required package manager
#===============================================================================

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# --- Constants ---

IDB_PYTHON_VERSION="3.13"

# --- Functions ---

command_exists() {
    command -v "$1" &> /dev/null
}

# --- Main ---

log_step "Installing idb"

export PATH="$HOME/.local/bin:$PATH"

if ! command_exists brew; then
    log_error "Homebrew is not installed. Please run: make set-up/homebrew"
    exit 1
fi

if ! command_exists uv; then
    log_error "uv is not installed. Please run: make set-up/dependencies"
    exit 1
fi

if ! command_exists idb_companion; then
    echo "Installing idb companion from Brewfile..."
    trust_third_party_formulae
    brew bundle install --file "$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)/Brewfile"
else
    log_skip "idb companion already installed"
fi

if ! uv tool list | grep -q '^fb-idb '; then
    echo "Installing idb client with uv..."
    uv tool install --python "$IDB_PYTHON_VERSION" fb-idb
else
    echo "Upgrading idb client with uv..."
    uv tool upgrade --python "$IDB_PYTHON_VERSION" fb-idb
fi

echo ""
echo "Verifying idb installation..."

if ! command_exists idb_companion; then
    log_error "idb_companion was not found on PATH after installation"
    exit 1
fi

if ! command_exists idb; then
    log_error "idb was not found on PATH after installation"
    echo "Ensure ~/.local/bin is on PATH. Knapsack manages this in ~/.zshenv."
    exit 1
fi

idb --help > /dev/null
idb_companion --version > /dev/null 2>&1

log_success "idb setup complete"
