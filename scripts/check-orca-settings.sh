#!/usr/bin/env bash
#===============================================================================
#  check-orca-settings.sh — Verify Orca's live settings match the tracked base and overlay
#
#  USAGE:
#    ./scripts/check-orca-settings.sh
#    source ./scripts/check-orca-settings.sh && check_orca_settings
#===============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/orca-settings.sh"

# Read-only: the live .settings must contain base * overlay. Reports drift by
# key name only, never values. Skips cleanly if Orca isn't installed or has
# never launched.
check_orca_settings() {
    local base="${ORCA_SETTINGS_BASE:-$REPO_ROOT/dotfiles/merge/orca/settings.json}"
    local overlay="${ORCA_SETTINGS_OVERLAY:-$HOME/.orca/settings.machine.json}"
    local data_file composed live_settings drift_keys

    if [[ ! -f "$base" ]]; then
        log_skip "no Orca settings base found, skipping"
        return 0
    fi

    if ! command -v jq > /dev/null 2>&1; then
        log_error "jq is required to check Orca settings"
        return 2
    fi

    if ! data_file="$(orca_active_data_file)"; then
        log_skip "Orca has never launched; skipping drift check"
        return 0
    fi

    if ! composed="$(compose_orca_settings "$base" "$overlay")"; then
        log_error "could not compose expected Orca settings"
        return 1
    fi

    if ! live_settings="$(jq -c '.settings // {}' "$data_file" 2> /dev/null)"; then
        log_error "could not read live settings from $data_file"
        return 1
    fi

    drift_keys="$(jq -r -n --argjson live "$live_settings" --argjson expected "$composed" '
        def applied($l; $e):
            if ($l | type) == "object" and ($e | type) == "object" then ($l * $e) == $l
            else $l == $e end;
        ($expected | keys[]) as $key |
        select(applied($live[$key]; $expected[$key]) | not) | $key
    ' 2> /dev/null | paste -sd ', ' -)"

    if [[ -n "$drift_keys" ]]; then
        log_error "live Orca settings drift from the composed base and overlay in keys: $drift_keys; run make set-up/orca"
        return 1
    fi

    log_success "live Orca settings match the composed base and overlay"
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    check_orca_settings
    exit $?
fi
