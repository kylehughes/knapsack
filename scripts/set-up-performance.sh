#!/usr/bin/env bash
#===============================================================================
#  set-up-performance.sh — Tune macOS for heavy parallel development
#
#  USAGE:
#    ./scripts/set-up-performance.sh
#
#  EXIT CODES:
#    0  success
#    1  not running on macOS
#
#  Applies idempotent, reversible system tunings for machines that run many
#  concurrent simulators and builds. Destructive periodic reclaim (clearing
#  DerivedData, pruning simulators) lives in the xcode-reclaim-space function.
#===============================================================================

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# --- Main ---

log_step "Tuning macOS for heavy parallel development"

if [[ "$(uname -s)" != "Darwin" ]]; then
    log_error "This script only applies to macOS."
    exit 1
fi

# --- Build Parallelism ---

# Cap compile tasks per build so many concurrent builds do not oversubscribe
# the CPU. Both Xcode and xcodebuild honor this default.
defaults write com.apple.dt.Xcode IDEBuildOperationMaxNumberOfConcurrentCompileTasks -int 2
log_success "Capped Xcode compile tasks per build to 2"

# --- Foreground Responsiveness ---

# Keep background terminals and agents at full speed instead of napping.
defaults write NSGlobalDomain NSAppSleepDisabled -bool true
log_success "Disabled App Nap"

# Remove window and Dock animations to reduce WindowServer load under many
# simulator windows.
defaults write NSGlobalDomain NSAutomaticWindowAnimationsEnabled -bool false
defaults write NSGlobalDomain NSWindowResizeTime -float 0.001
defaults write com.apple.dock expose-animation-duration -float 0
defaults write com.apple.dock autohide-time-modifier -float 0
killall Dock 2>/dev/null || true
log_success "Disabled window and Dock animations"

# --- Time Machine Exclusions ---

# Keep high-churn build output out of local snapshots and NAS backups.
exclude_from_time_machine() {
    local path="$1"
    if [[ ! -e "$path" ]]; then
        log_skip "Not present, skipping Time Machine exclusion: $path"
        return
    fi
    if tmutil isexcluded "$path" | grep -q '\[Excluded\]'; then
        log_skip "Already excluded from Time Machine: $path"
        return
    fi
    sudo tmutil addexclusion "$path"
    log_success "Excluded from Time Machine: $path"
}

exclude_from_time_machine "$HOME/Library/Developer/Xcode/DerivedData"
exclude_from_time_machine "$HOME/Library/Developer/CoreSimulator"

# --- Power ---

# Power Nap wakes the machine for background work; disable it so nothing steals
# cycles mid-run.
sudo pmset -a powernap 0
log_success "Disabled Power Nap"

echo ""
log_success "Performance tuning complete"
echo "Cooling (a stand or clamshell with an external display) is the main lever"
echo "for sustained clocks under load. Use xcode-reclaim-space to reclaim disk."
