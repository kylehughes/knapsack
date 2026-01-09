#!/bin/bash
# migrate-to-mise.sh - Migrate from nvm/rbenv/pyenv to mise.
# Usage: ./scripts/migrate-to-mise.sh

set -euo pipefail

# --- Constants ---

PROFILE="$HOME/.profile"

# --- Functions ---

log_step() {
    echo ""
    echo "→ $1"
}

log_success() {
    echo "✓ $1"
}

log_skip() {
    echo "⊘ $1"
}

get_node_version() {
    if [[ -f "$HOME/.nvm/alias/default" ]]; then
        cat "$HOME/.nvm/alias/default"
    elif [[ -d "$HOME/.nvm/versions/node" ]]; then
        ls "$HOME/.nvm/versions/node" | sort -V | tail -1 | tr -d 'v'
    else
        echo ""
    fi
}

get_ruby_version() {
    if command -v rbenv &> /dev/null; then
        rbenv version-name 2>/dev/null || echo ""
    else
        echo ""
    fi
}

get_python_version() {
    if command -v pyenv &> /dev/null; then
        pyenv version-name 2>/dev/null || echo ""
    else
        echo ""
    fi
}

# --- Main ---

echo "Migrating to mise (unified version manager)"
echo "============================================"

# Step 1: Install mise if needed.
log_step "Checking mise installation"
if command -v mise &> /dev/null; then
    log_success "mise already installed ($(mise --version | head -1))"
else
    echo "Installing mise via Homebrew..."
    brew install mise
    log_success "mise installed"
fi

# Step 2: Detect current versions.
log_step "Detecting current tool versions"

NODE_VERSION=$(get_node_version)
RUBY_VERSION=$(get_ruby_version)
PYTHON_VERSION=$(get_python_version)

[[ -n "$NODE_VERSION" ]] && echo "  Node: $NODE_VERSION" || echo "  Node: (not found)"
[[ -n "$RUBY_VERSION" ]] && echo "  Ruby: $RUBY_VERSION" || echo "  Ruby: (not found)"
[[ -n "$PYTHON_VERSION" ]] && echo "  Python: $PYTHON_VERSION" || echo "  Python: (not found)"

# Step 3: Install versions in mise.
log_step "Installing versions in mise"

if [[ -n "$NODE_VERSION" ]]; then
    echo "  Installing node@$NODE_VERSION..."
    mise use --global "node@$NODE_VERSION" 2>&1 | grep -E '(install|✓)' || true
fi

if [[ -n "$RUBY_VERSION" && "$RUBY_VERSION" != "system" ]]; then
    echo "  Installing ruby@$RUBY_VERSION..."
    mise use --global "ruby@$RUBY_VERSION" 2>&1 | grep -E '(install|✓)' || true
fi

if [[ -n "$PYTHON_VERSION" && "$PYTHON_VERSION" != "system" ]]; then
    echo "  Installing python@$PYTHON_VERSION..."
    mise use --global "python@$PYTHON_VERSION" 2>&1 | grep -E '(install|✓)' || true
fi

log_success "Versions installed in mise"

# Step 4: Clean up ~/.profile if it exists and contains version manager setup.
log_step "Cleaning up ~/.profile"

if [[ -f "$PROFILE" ]]; then
    if grep -qE '(nvm\.sh|rbenv init|pyenv init)' "$PROFILE"; then
        # Backup original.
        cp "$PROFILE" "$PROFILE.bak"
        echo "  Backed up to $PROFILE.bak"

        # Create cleaned version keeping non-version-manager lines.
        grep -vE '(nvm|rbenv|pyenv)' "$PROFILE" | grep -v '^$' | cat -s > "$PROFILE.tmp" || true

        # If file is empty or only whitespace, remove it.
        if [[ ! -s "$PROFILE.tmp" ]] || ! grep -q '[^[:space:]]' "$PROFILE.tmp"; then
            rm -f "$PROFILE" "$PROFILE.tmp"
            log_success "Removed empty ~/.profile"
        else
            mv "$PROFILE.tmp" "$PROFILE"
            log_success "Cleaned ~/.profile (backup at ~/.profile.bak)"
        fi
    else
        log_skip "~/.profile doesn't contain version manager setup"
    fi
else
    log_skip "~/.profile doesn't exist"
fi

# Step 5: Prompt for cleanup.
log_step "Old version manager cleanup"

CLEANUP_ITEMS=()
[[ -d "$HOME/.nvm" ]] && CLEANUP_ITEMS+=("~/.nvm")
[[ -d "$HOME/.rbenv" ]] && CLEANUP_ITEMS+=("~/.rbenv")
[[ -d "$HOME/.pyenv" ]] && CLEANUP_ITEMS+=("~/.pyenv")

if [[ ${#CLEANUP_ITEMS[@]} -gt 0 ]]; then
    echo "  Found: ${CLEANUP_ITEMS[*]}"
    echo ""
    echo "  To remove old version managers, run:"
    echo "    brew uninstall nvm rbenv pyenv 2>/dev/null || true"
    echo "    rm -rf ~/.nvm ~/.rbenv ~/.pyenv"
else
    log_skip "No old version manager directories found"
fi

# Done.
echo ""
echo "============================================"
log_success "Migration complete!"
echo ""
echo "Open a new terminal and verify with:"
echo "  mise doctor"
echo "  node --version && ruby --version && python3 --version"
