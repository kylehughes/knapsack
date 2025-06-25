#!/bin/bash
# set-up-local-functions.sh - Create local functions directory for machine-specific functions.
# Usage: ./scripts/set-up-local-functions.sh

set -euo pipefail

# --- Constants ---

LOCAL_FUNCTIONS_DIR="$HOME/.config/zsh/functions-local"

# --- Main ---

# Create directory if it doesn't exist.
if [[ ! -d "$LOCAL_FUNCTIONS_DIR" ]]; then
    echo "Creating local functions directory: $LOCAL_FUNCTIONS_DIR"
    mkdir -p "$LOCAL_FUNCTIONS_DIR"
    
    # Create example function.
    cat > "$LOCAL_FUNCTIONS_DIR/example-local" << 'EOF'
#!/usr/bin/env zsh
# example-local - Example local function (delete or rename).
# Usage: example-local

echo "This is a local function only on this machine!"
echo "Add your machine-specific functions to: ~/.config/zsh/functions-local/"
EOF
    
    chmod +x "$LOCAL_FUNCTIONS_DIR/example-local"
    echo "✓ Created example function: example-local"
else
    echo "Local functions directory already exists: $LOCAL_FUNCTIONS_DIR"
fi

echo ""
echo "To create a new local function:"
echo "1. Create file: ~/.config/zsh/functions-local/function-name"
echo "2. Make executable: chmod +x ~/.config/zsh/functions-local/function-name"
echo "3. Restart shell or run: source ~/.zshrc"