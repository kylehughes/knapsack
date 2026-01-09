#!/usr/bin/env bash
#===============================================================================
#  set-up-local-functions.sh — Create local functions directory
#
#  USAGE:
#    ./scripts/set-up-local-functions.sh
#
#  Creates ~/.config/zsh/functions-local/ for machine-specific shell functions
#  that are not tracked in git.
#
#  EXIT CODES:
#    0  success (directory created or already exists)
#===============================================================================

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# --- Constants ---

LOCAL_FUNCTIONS_DIR="$HOME/.config/zsh/functions-local"

# --- Main ---

log_step "Setting up local functions directory"

if [[ ! -d "$LOCAL_FUNCTIONS_DIR" ]]; then
    mkdir -p "$LOCAL_FUNCTIONS_DIR"

    cat > "$LOCAL_FUNCTIONS_DIR/example-local" << 'EOF'
#!/usr/bin/env zsh
# example-local - Example local function (delete or rename).
# Usage: example-local

echo "This is a local function only on this machine!"
echo "Add your machine-specific functions to: ~/.config/zsh/functions-local/"
EOF

    chmod +x "$LOCAL_FUNCTIONS_DIR/example-local"
    log_success "Created $LOCAL_FUNCTIONS_DIR with example function"
else
    log_skip "Directory already exists: $LOCAL_FUNCTIONS_DIR"
fi

echo ""
echo "To create a new local function:"
echo "  1. Create file: ~/.config/zsh/functions-local/function-name"
echo "  2. Make executable: chmod +x ~/.config/zsh/functions-local/function-name"
echo "  3. Restart shell or run: source ~/.zshrc"
