#!/usr/bin/env bash
# Fixture tests for the Orca settings tooling: lib helpers, apply, capture,
# and the drift check. Never touches the real HOME or live Orca data.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/orca-settings-test.XXXXXX")"

cleanup() { rm -rf "$FIXTURE_ROOT"; }
trap cleanup EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
write_json() { printf '%s\n' "$2" > "$1"; }
assert_json() { jq -e "$2" "$1" > /dev/null || fail "unexpected JSON in $1: $2"; }

PROFILE_ID="11111111-1111-1111-1111-111111111111"
DATA_DIR="$FIXTURE_ROOT/data"
BASE="$FIXTURE_ROOT/base.json"
OVERLAY="$FIXTURE_ROOT/overlay.json"

make_data_file() {
    mkdir -p "$DATA_DIR/profiles/$PROFILE_ID"
    write_json "$DATA_DIR/orca-profile-index.json" "{\"activeProfileId\":\"$PROFILE_ID\"}"
    write_json "$DATA_DIR/profiles/$PROFILE_ID/orca-data.json" \
        '{"repos":["repo-a"],"sessions":{"count":3},"settings":{"theme":"dark","branchPrefix":"kh/","terminalQuickCommands":[{"label":"global","scope":{"type":"global"}}]}}'
}

env_for() {
    ORCA_USER_DATA_PATH="$DATA_DIR" \
    ORCA_SETTINGS_BASE="$BASE" \
    ORCA_SETTINGS_OVERLAY="$OVERLAY" \
    ORCA_PROCESS_CHECK_COMMAND="${ORCA_PROCESS_CHECK_COMMAND:-false}" \
    "$@"
}

# --- lib: compose ---

source "$SCRIPT_DIR/../lib/orca-settings.sh"

write_json "$BASE" '{"nested":{"base":true},"array":[1],"theme":"dark"}'
write_json "$OVERLAY" '{"nested":{"overlay":true},"array":[2]}'
output="$(compose_orca_settings "$BASE" "$OVERLAY")"
printf '%s' "$output" | jq -e '.nested == {"base":true,"overlay":true} and .array == [2] and .theme == "dark"' > /dev/null \
    || fail "compose did not deep-merge objects and replace arrays"

output="$(compose_orca_settings "$BASE" "$FIXTURE_ROOT/missing-overlay.json")"
printf '%s' "$output" | jq -e '.theme == "dark" and .array == [1]' > /dev/null \
    || fail "compose did not tolerate a missing overlay"

# --- lib: base denylist, key names only ---

denylist_cases=(
    'claudeManagedAccounts|{"claudeManagedAccounts":{"secret":"DO_NOT_PRINT_1"}}'
    'opencodeSessionCookie|{"opencodeSessionCookie":"DO_NOT_PRINT_2"}'
    'somethingMigrated|{"somethingMigrated":"DO_NOT_PRINT_3"}'
    'defaultedFoo|{"fooDefaultedBar":"DO_NOT_PRINT_4"}'
    'tabSwitchKeybindingSeed|{"tabSwitchKeybindingSeed":"DO_NOT_PRINT_5"}'
    'userpath|{"nested":{"path":"/Users/kyle/DO_NOT_PRINT_6"}}'
)
for case in "${denylist_cases[@]}"; do
    label="${case%%|*}"
    json="${case#*|}"
    invalid="$FIXTURE_ROOT/invalid-$label.json"
    write_json "$invalid" "$json"
    if orca_validate_base_file "$invalid" "base" 2> "$FIXTURE_ROOT/error.log"; then
        fail "$label base unexpectedly passed validation"
    fi
    grep -q 'DO_NOT_PRINT' "$FIXTURE_ROOT/error.log" && fail "$label diagnostic exposed a value"
done

write_json "$FIXTURE_ROOT/invalid-repo-scope.json" \
    '{"terminalQuickCommands":[{"label":"DO_NOT_PRINT_7","scope":{"type":"repo","repoId":"abc"}}]}'
if orca_validate_base_file "$FIXTURE_ROOT/invalid-repo-scope.json" "base" 2> "$FIXTURE_ROOT/error.log"; then
    fail "repo-scoped quick command unexpectedly passed validation"
fi
grep -q 'DO_NOT_PRINT' "$FIXTURE_ROOT/error.log" && fail "repo-scope diagnostic exposed a value"

write_json "$FIXTURE_ROOT/valid-global-scope.json" \
    '{"terminalQuickCommands":[{"label":"ok","scope":{"type":"global"}}]}'
orca_validate_base_file "$FIXTURE_ROOT/valid-global-scope.json" "base" \
    || fail "global-scoped quick command incorrectly rejected"

# Overlay gets only a shape check; secrets and machine paths are allowed there.
write_json "$FIXTURE_ROOT/overlay-with-secret.json" '{"opencodeSessionCookie":"fine-on-overlay","path":"/Users/kyle/x"}'
orca_validate_overlay_file "$FIXTURE_ROOT/overlay-with-secret.json" "overlay" \
    || fail "overlay incorrectly rejected a value allowed only on the base"

write_json "$FIXTURE_ROOT/overlay-not-object.json" '[1,2,3]'
if orca_validate_overlay_file "$FIXTURE_ROOT/overlay-not-object.json" "overlay" 2> /dev/null; then
    fail "non-object overlay unexpectedly passed validation"
fi

# --- apply: happy path patches only .settings, backs up, logs changed keys ---

make_data_file
write_json "$BASE" '{"theme":"light","branchPrefix":"kh/","terminalQuickCommands":[{"label":"a","scope":{"type":"global"}},{"label":"b","scope":{"type":"global"}}]}'
rm -f "$OVERLAY"

data_file="$DATA_DIR/profiles/$PROFILE_ID/orca-data.json"
before_non_settings="$(jq -S 'del(.settings)' "$data_file")"

env_for bash "$PROJECT_ROOT/scripts/set-up-orca-settings.sh" > "$FIXTURE_ROOT/apply.log" 2>&1 \
    || fail "apply failed: $(cat "$FIXTURE_ROOT/apply.log")"

[[ -f "$OVERLAY" ]] || fail "apply did not create a missing overlay"
assert_json "$OVERLAY" '. == {}'

after_non_settings="$(jq -S 'del(.settings)' "$data_file")"
[[ "$before_non_settings" == "$after_non_settings" ]] || fail "apply changed data outside .settings"

assert_json "$data_file" '.settings.theme == "light" and .settings.branchPrefix == "kh/" and (.settings.terminalQuickCommands | length) == 2'
[[ -f "$DATA_DIR/profiles/$PROFILE_ID/orca-data.json.pre-knapsack" ]] || fail "apply did not write a backup"
grep -q "theme" "$FIXTURE_ROOT/apply.log" || fail "apply did not log the changed settings key"

# --- apply: overlay wins over base ---

write_json "$OVERLAY" '{"theme":"overlay-wins"}'
env_for bash "$PROJECT_ROOT/scripts/set-up-orca-settings.sh" > /dev/null \
    || fail "apply with overlay failed"
assert_json "$data_file" '.settings.theme == "overlay-wins"'

# --- apply: no-op run does not rewrite the file ---

before_hash="$(shasum "$data_file")"
before_backup_hash="$(shasum "$DATA_DIR/profiles/$PROFILE_ID/orca-data.json.pre-knapsack")"
env_for bash "$PROJECT_ROOT/scripts/set-up-orca-settings.sh" > "$FIXTURE_ROOT/noop.log" 2>&1 \
    || fail "no-op apply failed"
after_hash="$(shasum "$data_file")"
after_backup_hash="$(shasum "$DATA_DIR/profiles/$PROFILE_ID/orca-data.json.pre-knapsack")"
[[ "$before_hash" == "$after_hash" ]] || fail "no-op apply rewrote the data file"
[[ "$before_backup_hash" == "$after_backup_hash" ]] || fail "no-op apply rewrote the backup"
grep -qi "up to date" "$FIXTURE_ROOT/noop.log" || fail "no-op apply did not report up to date"

# --- apply: running Orca skips with nothing written ---

before_hash="$(shasum "$data_file")"
ORCA_PROCESS_CHECK_COMMAND=true env_for bash "$PROJECT_ROOT/scripts/set-up-orca-settings.sh" > "$FIXTURE_ROOT/running.log" 2>&1 \
    || fail "apply while running should exit 0"
after_hash="$(shasum "$data_file")"
[[ "$before_hash" == "$after_hash" ]] || fail "apply while Orca is running modified the data file"
grep -qi "running" "$FIXTURE_ROOT/running.log" || fail "apply while running did not explain the skip"

# --- apply: missing index/data file skips without creating anything ---

empty_data_dir="$FIXTURE_ROOT/empty-data"
mkdir -p "$empty_data_dir"
ORCA_USER_DATA_PATH="$empty_data_dir" ORCA_SETTINGS_BASE="$BASE" ORCA_SETTINGS_OVERLAY="$OVERLAY" ORCA_PROCESS_CHECK_COMMAND=false \
    bash "$PROJECT_ROOT/scripts/set-up-orca-settings.sh" > "$FIXTURE_ROOT/missing.log" 2>&1 \
    || fail "apply with no launched Orca should exit 0"
[[ -z "$(find "$empty_data_dir" -mindepth 1)" ]] || fail "apply created files for a never-launched Orca"
grep -qi "never launched" "$FIXTURE_ROOT/missing.log" || fail "apply did not explain the never-launched skip"

# --- apply: denylisted base is rejected without writing ---

write_json "$FIXTURE_ROOT/bad-base.json" '{"telemetry":{"enabled":true,"id":"DO_NOT_PRINT_8"}}'
before_hash="$(shasum "$data_file")"
if ORCA_USER_DATA_PATH="$DATA_DIR" ORCA_SETTINGS_BASE="$FIXTURE_ROOT/bad-base.json" ORCA_SETTINGS_OVERLAY="$OVERLAY" ORCA_PROCESS_CHECK_COMMAND=false \
    bash "$PROJECT_ROOT/scripts/set-up-orca-settings.sh" > "$FIXTURE_ROOT/bad-base.log" 2>&1; then
    fail "apply with a denylisted base unexpectedly succeeded"
fi
after_hash="$(shasum "$data_file")"
[[ "$before_hash" == "$after_hash" ]] || fail "apply with a denylisted base modified the data file"
grep -q 'DO_NOT_PRINT' "$FIXTURE_ROOT/bad-base.log" && fail "apply exposed a denylisted value"

# --- capture: refreshes only existing base keys, never adds ---

write_json "$BASE" '{"theme":"light","branchPrefix":"kh/","voice":{"enabled":false}}'
write_json "$OVERLAY" '{}'
# Live settings gain a new key, change an existing one, and carry a sibling
# beside a partially pinned object; capture must refresh "theme" and
# "voice.enabled" but never introduce "newSetting" or "voice.microphone".
jq '.settings = {"theme":"live-value","branchPrefix":"kh/","newSetting":"should-not-appear","voice":{"enabled":true,"microphone":"should-not-appear"}}' "$data_file" > "$FIXTURE_ROOT/tmp.json"
mv "$FIXTURE_ROOT/tmp.json" "$data_file"

env_for bash "$PROJECT_ROOT/scripts/capture-orca-settings.sh" > "$FIXTURE_ROOT/capture.log" 2>&1 \
    || fail "capture failed: $(cat "$FIXTURE_ROOT/capture.log")"
assert_json "$BASE" '.theme == "live-value" and .branchPrefix == "kh/" and (has("newSetting") | not) and .voice == {"enabled":true}'

# --- capture: refuses to write a result that fails validation ---

write_json "$BASE" '{"branchPrefix":"kh/"}'
jq '.settings = {"branchPrefix":"/Users/kyle/DO_NOT_PRINT_9"}' "$data_file" > "$FIXTURE_ROOT/tmp.json"
mv "$FIXTURE_ROOT/tmp.json" "$data_file"
before_base="$(cat "$BASE")"
if env_for bash "$PROJECT_ROOT/scripts/capture-orca-settings.sh" > "$FIXTURE_ROOT/capture-bad.log" 2>&1; then
    fail "capture unexpectedly wrote a base that fails validation"
fi
[[ "$(cat "$BASE")" == "$before_base" ]] || fail "capture modified the base despite failing validation"
grep -q 'DO_NOT_PRINT' "$FIXTURE_ROOT/capture-bad.log" && fail "capture exposed a rejected value"

# --- capture: refuses to run while Orca is running ---

write_json "$BASE" '{"branchPrefix":"kh/"}'
jq '.settings = {"branchPrefix":"kh/"}' "$data_file" > "$FIXTURE_ROOT/tmp.json"
mv "$FIXTURE_ROOT/tmp.json" "$data_file"
before_base="$(cat "$BASE")"
ORCA_PROCESS_CHECK_COMMAND=true env_for bash "$PROJECT_ROOT/scripts/capture-orca-settings.sh" > "$FIXTURE_ROOT/capture-running.log" 2>&1 \
    || fail "capture while running should exit 0"
[[ "$(cat "$BASE")" == "$before_base" ]] || fail "capture while Orca is running modified the base"

# --- check: passes after apply, fails (key names only) after drift ---

write_json "$BASE" '{"theme":"light","branchPrefix":"kh/","voice":{"enabled":true}}'
write_json "$OVERLAY" '{}'
# Live siblings beside a partially pinned object are not drift.
jq '.settings = {"theme":"light","branchPrefix":"kh/","voice":{"enabled":true,"microphone":"local"}}' "$data_file" > "$FIXTURE_ROOT/tmp.json"
mv "$FIXTURE_ROOT/tmp.json" "$data_file"

source "$PROJECT_ROOT/scripts/check-orca-settings.sh"
ORCA_USER_DATA_PATH="$DATA_DIR" ORCA_SETTINGS_BASE="$BASE" ORCA_SETTINGS_OVERLAY="$OVERLAY" \
    check_orca_settings > "$FIXTURE_ROOT/check-pass.log" 2>&1 \
    || fail "check should pass when live settings match the composed base and overlay"

jq '.settings.theme = "drifted"' "$data_file" > "$FIXTURE_ROOT/tmp.json"
mv "$FIXTURE_ROOT/tmp.json" "$data_file"
if ORCA_USER_DATA_PATH="$DATA_DIR" ORCA_SETTINGS_BASE="$BASE" ORCA_SETTINGS_OVERLAY="$OVERLAY" \
    check_orca_settings > "$FIXTURE_ROOT/check-fail.log" 2>&1; then
    fail "check should fail after drift"
fi
grep -q 'theme' "$FIXTURE_ROOT/check-fail.log" || fail "check did not report the drifted key"

jq '.settings.theme = "light" | .settings.voice.enabled = false' "$data_file" > "$FIXTURE_ROOT/tmp.json"
mv "$FIXTURE_ROOT/tmp.json" "$data_file"
if ORCA_USER_DATA_PATH="$DATA_DIR" ORCA_SETTINGS_BASE="$BASE" ORCA_SETTINGS_OVERLAY="$OVERLAY" \
    check_orca_settings > "$FIXTURE_ROOT/check-nested.log" 2>&1; then
    fail "check should fail after nested drift"
fi
grep -q 'voice' "$FIXTURE_ROOT/check-nested.log" || fail "check did not report the nested drifted key"

echo "Orca settings tests passed"
