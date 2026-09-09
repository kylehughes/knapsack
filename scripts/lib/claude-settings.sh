#!/usr/bin/env bash
# Shared composition support for Claude Code settings.

_claude_settings_error() {
    echo "claude settings: $*" >&2
}

_claude_settings_validate_file() {
    local path="$1"
    local label="$2"

    if [[ ! -f "$path" ]]; then
        _claude_settings_error "$label is not a regular file"
        return 1
    fi

    if ! jq -e -s '
        length == 1
        and (.[0] | type == "object")
        and (if .[0] | has("enabledPlugins") then .[0].enabledPlugins | type == "object" else true end)
        and (if .[0] | has("extraKnownMarketplaces") then .[0].extraKnownMarketplaces | type == "object" else true end)
    ' "$path" > /dev/null 2>&1; then
        _claude_settings_error "$label must contain exactly one JSON object with object plugin fields"
        return 1
    fi
}

# Deep-merge the required tracked base with an optional local overlay. jq's *
# recursively merges objects, including plugin maps, and replaces arrays.
compose_claude_settings() {
    if [[ $# -ne 2 ]]; then
        _claude_settings_error "compose requires BASE and OVERLAY paths"
        return 2
    fi

    local base="$1"
    local overlay="$2"
    local overlay_input=/dev/null

    _claude_settings_validate_file "$base" "base" || return

    if [[ -e "$overlay" ]]; then
        _claude_settings_validate_file "$overlay" "overlay" || return
        overlay_input="$overlay"
    elif [[ -L "$overlay" ]]; then
        _claude_settings_error "overlay is a dangling symlink"
        return 1
    fi

    if ! jq -s '.[0] * (.[1] // {})' "$base" "$overlay_input" 2> /dev/null; then
        _claude_settings_error "could not compose settings"
        return 1
    fi
}
