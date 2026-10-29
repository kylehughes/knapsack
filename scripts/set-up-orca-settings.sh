#!/usr/bin/env bash
#===============================================================================
#  set-up-orca-settings.sh — Patch Orca's live settings from the tracked base and overlay
#
#  USAGE:
#    ./scripts/set-up-orca-settings.sh
#
#  Patches only the .settings key of the active Orca profile's data file with
#  base * overlay, leaving every other top-level key (repos, sessions,
#  worktree metadata) untouched. Orca writes that file from memory on a
#  debounce and on quit, with no file watcher, so this script refuses to run
#  while Orca is open and skips cleanly rather than failing `make set-up/all`.
#
#  REQUIREMENTS:
#    bash >= 3.x, jq
#
#  EXIT CODES:
#    0  success, or a clean skip (no base, Orca running, Orca never launched)
#    2  missing dependency
#    3  script-specific failure (invalid input, patch could not be verified)
#
#  AUTHOR:      Kyle Hughes <kyle@kylehugh.es>
#  LICENSE:     MIT
#===============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/orca-settings.sh"

BASE="${ORCA_SETTINGS_BASE:-$REPO_ROOT/dotfiles/merge/orca/settings.json}"
OVERLAY="${ORCA_SETTINGS_OVERLAY:-$HOME/.orca/settings.machine.json}"

log_step "Setting up Orca settings"

if [[ ! -f "$BASE" ]]; then
    log_skip "no Orca settings base found, skipping"
    exit 0
fi

if ! command -v jq > /dev/null 2>&1; then
    log_error "jq is required to merge Orca settings"
    exit 2
fi

if orca_is_running; then
    log_skip "Orca is running; quit Orca, then run 'make set-up/orca'"
    exit 0
fi

if ! DATA_FILE="$(orca_active_data_file)"; then
    log_skip "Orca has never launched; launch Orca once, then rerun 'make set-up/orca'"
    exit 0
fi

orca_validate_base_file "$BASE" "base" || exit 3

mkdir -p "$(dirname "$OVERLAY")"
if [[ ! -e "$OVERLAY" ]]; then
    log_success "creating empty overlay at $OVERLAY"
    echo '{}' > "$OVERLAY"
fi

orca_validate_overlay_file "$OVERLAY" "overlay" || exit 3

DATA_DIR="$(dirname "$DATA_FILE")"
BACKUP="$DATA_DIR/orca-data.json.pre-knapsack"
TEMP="$(mktemp "$DATA_DIR/.orca-data.json.tmp.XXXXXX")"
trap 'rm -f "$TEMP"' EXIT

if ! orca_patch_data_file "$DATA_FILE" "$BASE" "$OVERLAY" > "$TEMP"; then
    log_error "could not patch $DATA_FILE"
    exit 3
fi

if ! jq -e . "$TEMP" > /dev/null 2>&1; then
    log_error "patched data file did not parse; aborting without writing"
    exit 3
fi

if ! orca_non_settings_match "$DATA_FILE" "$TEMP"; then
    log_error "patch changed data outside .settings; aborting without writing"
    exit 3
fi

if cmp -s <(jq -S . "$DATA_FILE") <(jq -S . "$TEMP"); then
    log_skip "Orca settings already up to date"
    exit 0
fi

# Runtime state and every other top-level key are untouched by construction
# (orca_non_settings_match already proved it); report only the settings keys
# this patch changes.
DRIFT_KEYS="$(jq -r -s '
    .[0].settings as $current | .[1].settings as $desired |
    [($current | keys[]), ($desired | keys[])] | unique[] as $key |
    select((($current | has($key)) != ($desired | has($key)))
        or (($current[$key]) != ($desired[$key]))) | $key
' "$DATA_FILE" "$TEMP" 2> /dev/null | paste -sd ', ' -)"

cp "$DATA_FILE" "$BACKUP"
mv -f "$TEMP" "$DATA_FILE"

log_success "patched $DATA_FILE (changed settings: ${DRIFT_KEYS:-none})"
