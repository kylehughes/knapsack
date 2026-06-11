#!/usr/bin/env bash
#===============================================================================
#  common.sh — Shared utilities for setup scripts
#
#  USAGE:
#    source "$(dirname "$0")/lib/common.sh"
#
#  FUNCTIONS:
#    log_step     Print a step header (→)
#    log_success  Print a success message (✓)
#    log_skip     Print a skip message (⊘)
#    log_error    Print an error message to stderr (✗)
#    trust_homebrew_formula  Trust a third-party Homebrew formula when supported
#===============================================================================

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

log_error() {
    echo "✗ $1" >&2
}

trust_homebrew_formula() {
    local formula="$1"

    # Homebrew 6 can require explicit trust before loading third-party formulae.
    if brew help trust > /dev/null 2>&1; then
        brew trust --formula "$formula"
    fi
}
