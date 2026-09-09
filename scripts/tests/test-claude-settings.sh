#!/usr/bin/env bash
# Fixture tests for the Claude settings compositor.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/../lib/claude-settings.sh"

test_directory="$(mktemp -d "${TMPDIR:-/tmp}/claude-settings-test.XXXXXX")"
trap 'rm -rf "$test_directory"' EXIT

fail() { echo "FAIL: $*" >&2; exit 1; }
write_json() { printf '%s\n' "$2" > "$1"; }
assert_json() { jq -e "$2" "$1" > /dev/null || fail "unexpected JSON in $1"; }

base="$test_directory/base.json"
overlay="$test_directory/overlay.json"
output="$test_directory/output.json"

write_json "$base" '{"nested":{"base":true},"array":[1],"enabledPlugins":{"base":true},"extraKnownMarketplaces":{"base":{}}}'
write_json "$overlay" '{"nested":{"overlay":true},"array":[2],"enabledPlugins":{"base":false,"overlay":false},"extraKnownMarketplaces":{"overlay":{}}}'
compose_claude_settings "$base" "$overlay" > "$output"
assert_json "$output" '.nested == {"base":true,"overlay":true} and .array == [2] and .enabledPlugins == {"base":false,"overlay":false} and .extraKnownMarketplaces == {"base":{},"overlay":{}}'

write_json "$overlay" '{"local":true}'
compose_claude_settings "$base" "$overlay" > "$output"
assert_json "$output" '.enabledPlugins == {"base":true} and .extraKnownMarketplaces == {"base":{}} and .local == true'

compose_claude_settings "$base" "$test_directory/missing-overlay.json" > "$output"
assert_json "$output" '.nested == {"base":true} and .array == [1] and .enabledPlugins == {"base":true}'

for invalid in malformed empty multiple plugin_type; do
    invalid_file="$test_directory/$invalid.json"
    case "$invalid" in
        malformed) printf '%s\n' '{"secret":"do-not-print"' > "$invalid_file" ;;
        empty) : > "$invalid_file" ;;
        multiple) printf '%s\n%s\n' '{}' '{}' > "$invalid_file" ;;
        plugin_type) write_json "$invalid_file" '{"enabledPlugins":false}' ;;
    esac
    if compose_claude_settings "$base" "$invalid_file" > /dev/null 2> "$test_directory/error.log"; then
        fail "$invalid overlay unexpectedly composed"
    fi
    rg -q 'do-not-print' "$test_directory/error.log" && fail "diagnostic exposed a JSON value"
done

echo "Claude settings tests passed"
