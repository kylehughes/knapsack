#!/usr/bin/env bash
# Shared composition support for Orca settings. Mirrors lib/claude-settings.sh,
# with two differences: Orca's tracked base is validated against a denylist
# because Knapsack is public, and composition patches only the `.settings` key
# of Orca's live data file rather than regenerating the whole file.

_orca_settings_error() {
    echo "orca settings: $*" >&2
}

# The active profile's data directory. ORCA_USER_DATA_PATH redirects it, the
# same variable Orca itself honors.
orca_data_dir() {
    printf '%s' "${ORCA_USER_DATA_PATH:-$HOME/Library/Application Support/orca}"
}

# Resolve the active profile's data file. Prints the path on stdout. Returns 1
# without printing an error when Orca has never launched (no index, no active
# profile id, or no data file yet); callers treat that as a clean skip rather
# than a failure.
orca_active_data_file() {
    local data_dir index active_id data_file

    data_dir="$(orca_data_dir)"
    index="$data_dir/orca-profile-index.json"

    [[ -f "$index" ]] || return 1

    active_id="$(jq -r '.activeProfileId // empty' "$index" 2> /dev/null)"
    [[ -n "$active_id" ]] || return 1

    data_file="$data_dir/profiles/$active_id/orca-data.json"
    [[ -f "$data_file" ]] || return 1

    printf '%s' "$data_file"
}

# True if Orca is running. Orca debounces writes and flushes only on quit, so
# apply and capture must refuse to touch the file while it's open.
# ORCA_PROCESS_CHECK_COMMAND overrides the detection command for tests.
orca_is_running() {
    local check_command="${ORCA_PROCESS_CHECK_COMMAND:-pgrep -f /Orca.app/Contents/MacOS/Orca}"
    $check_command > /dev/null 2>&1
}

_orca_settings_validate_shape() {
    local path="$1"
    local label="$2"

    if [[ ! -f "$path" ]]; then
        _orca_settings_error "$label is not a regular file"
        return 1
    fi

    if ! jq -e -s 'length == 1 and (.[0] | type == "object")' "$path" > /dev/null 2>&1; then
        _orca_settings_error "$label must contain exactly one JSON object"
        return 1
    fi
}

# The overlay carries machine secrets and local paths, so it gets only the
# shape check.
orca_validate_overlay_file() {
    local path="$1"
    local label="${2:-overlay}"

    _orca_settings_validate_shape "$path" "$label"
}

# Reject a base file that isn't safe to publish. Reports offending key names
# only, never values, since Knapsack is a public repository.
orca_validate_base_file() {
    local path="$1"
    local label="${2:-base}"
    local reasons

    _orca_settings_validate_shape "$path" "$label" || return 1

    reasons="$(jq -r '
        def denylistExact: [
            "claudeManagedAccounts", "codexManagedAccounts",
            "activeClaudeManagedAccountId", "activeCodexManagedAccountId",
            "activeCodexManagedAccountIdsByRuntime", "activeRuntimeEnvironmentId",
            "telemetry", "workspaceDir", "workspaceDirHistory", "devPluginPaths",
            "androidSdkPath", "defaultRepoSelection", "defaultLinearTeamSelection",
            "githubProjects", "prBotAuthorOverrides", "floatingTerminalTrustedCwds",
            "mobilePairingCustomAddress", "mobilePairingCustomAddresses",
            "mobileEmulatorDefaultDeviceUdid", "localAccountWslDistro",
            "nativeChatSessionOptions"
        ];
        def denylistPrefix: ["opencode", "minimax", "httpProxy"];

        (
            [ keys[] as $k
              | select(
                    (denylistExact | index($k) != null)
                    or (denylistPrefix[] as $p | $k | startswith($p))
                    or ($k | test("Migrated"))
                    or ($k | test("Defaulted"))
                    or ($k | test("Seed$"))
                )
              | "denylisted key: " + $k
            ]
            +
            [ paths(strings) as $p
              | select(getpath($p) | test("/Users/"))
              | "value under key contains a /Users/ path: " + ($p[0] | tostring)
            ]
            +
            [ (.terminalQuickCommands? // [])[]?
              | select(.scope?.type? == "repo")
              | "terminalQuickCommands entry is scoped to a repo"
            ]
        ) | unique | .[]
    ' "$path" 2> /dev/null)"

    if [[ -n "$reasons" ]]; then
        _orca_settings_error "$label rejected: $(printf '%s' "$reasons" | paste -sd '; ' -)"
        return 1
    fi
}

# Compose the base and overlay into the settings that should be live, without
# touching the data file. Validates the base against the denylist and the
# overlay's shape.
compose_orca_settings() {
    if [[ $# -ne 2 ]]; then
        _orca_settings_error "compose requires BASE and OVERLAY paths"
        return 2
    fi

    local base="$1"
    local overlay="$2"
    local overlay_input=/dev/null

    orca_validate_base_file "$base" "base" || return

    if [[ -e "$overlay" ]]; then
        orca_validate_overlay_file "$overlay" "overlay" || return
        overlay_input="$overlay"
    elif [[ -L "$overlay" ]]; then
        _orca_settings_error "overlay is a dangling symlink"
        return 1
    fi

    if ! jq -s '.[0] * (.[1] // {})' "$base" "$overlay_input" 2> /dev/null; then
        _orca_settings_error "could not compose settings"
        return 1
    fi
}

# Patch a data file's .settings with base * overlay, leaving every other
# top-level key untouched. Callers must validate base and overlay first, and
# must pass an overlay path that exists (an empty object if there is none).
orca_patch_data_file() {
    if [[ $# -ne 3 ]]; then
        _orca_settings_error "patch requires DATA_FILE, BASE, and OVERLAY paths"
        return 2
    fi

    local data_file="$1"
    local base="$2"
    local overlay="$3"

    if ! jq --slurpfile base "$base" --slurpfile overlay "$overlay" '
        .settings = (.settings * $base[0] * $overlay[0])
    ' "$data_file" 2> /dev/null; then
        _orca_settings_error "could not patch data file"
        return 1
    fi
}

# True if two data files are byte-for-byte identical outside .settings.
orca_non_settings_match() {
    local original="$1"
    local patched="$2"

    cmp -s \
        <(jq -S 'del(.settings)' "$original" 2> /dev/null) \
        <(jq -S 'del(.settings)' "$patched" 2> /dev/null)
}

# Build a refreshed base: for every key already present in $base, use the live
# settings value if the key is present live, otherwise keep the base's own
# value. Objects recurse, so a base that pins part of a settings object never
# picks up the machine-specific siblings Orca stores beside it. Never adds a
# key that isn't already in the base; growing the allowlist is a deliberate
# edit to the base.
orca_capture_base() {
    if [[ $# -ne 2 ]]; then
        _orca_settings_error "capture requires BASE and LIVE_SETTINGS paths"
        return 2
    fi

    local base="$1"
    local live="$2"

    if ! jq -S -s '
        def refresh($base; $live):
            if ($base | type) == "object" and ($live | type) == "object" then
                reduce ($base | keys[]) as $k ($base;
                    if $live | has($k) then .[$k] = refresh($base[$k]; $live[$k]) else . end)
            else $live end;
        refresh(.[0]; .[1])
    ' "$base" "$live" 2> /dev/null; then
        _orca_settings_error "could not capture settings"
        return 1
    fi
}
