#!/usr/bin/env bash
#===============================================================================
#  capture-orca-settings.sh — Copy live Orca preference changes back into the tracked base
#
#  USAGE:
#    ./scripts/capture-orca-settings.sh
#
#  Orca's settings UI is the easiest place to change a preference; this script
#  copies those changes back. For every key already in the tracked base, it
#  takes Orca's live .settings value (or keeps the base's own value if the key
#  is missing live), rewrites the base with sorted keys, and prints a diff to
#  review before committing. It never adds a key: growing the allowlist is a
#  deliberate edit to the base. It refuses to run while Orca is open, since its
#  in-memory settings can lag the file on disk, the same as apply.
#
#  REQUIREMENTS:
#    bash >= 3.x, jq, git
#
#  EXIT CODES:
#    0  success, or a clean skip (no base, Orca running, Orca never launched)
#    2  missing dependency
#    3  script-specific failure (captured result failed base validation)
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

log_step "Capturing live Orca settings into the tracked base"

if [[ ! -f "$BASE" ]]; then
    log_skip "no Orca settings base found, skipping"
    exit 0
fi

if ! command -v jq > /dev/null 2>&1; then
    log_error "jq is required to capture Orca settings"
    exit 2
fi

if orca_is_running; then
    log_skip "Orca is running, and its in-memory settings can lag the file on disk; quit Orca, then run 'make capture/orca'"
    exit 0
fi

if ! DATA_FILE="$(orca_active_data_file)"; then
    log_skip "Orca has never launched; launch Orca once, then rerun 'make capture/orca'"
    exit 0
fi

LIVE="$(mktemp "${TMPDIR:-/tmp}/orca-live-settings.XXXXXX")"
CAPTURED="$(mktemp "${TMPDIR:-/tmp}/orca-captured-base.XXXXXX")"
trap 'rm -f "$LIVE" "$CAPTURED"' EXIT

if ! jq '.settings // {}' "$DATA_FILE" > "$LIVE" 2> /dev/null; then
    log_error "could not read live settings from $DATA_FILE"
    exit 3
fi

if ! orca_capture_base "$BASE" "$LIVE" > "$CAPTURED"; then
    exit 3
fi

# The step-3 validation also runs on the captured result, so a secret or path
# in the live settings can't slip into the public base.
if ! orca_validate_base_file "$CAPTURED" "captured base"; then
    log_error "captured settings failed validation; base left unchanged"
    exit 3
fi

if cmp -s "$BASE" "$CAPTURED"; then
    log_skip "captured Orca settings already match the tracked base"
    exit 0
fi

cp "$CAPTURED" "$BASE"
log_success "updated $BASE"
git -C "$REPO_ROOT" diff --stat -- dotfiles/merge/orca/settings.json
