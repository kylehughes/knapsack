#!/usr/bin/env bash
#===============================================================================
#  check-agents.sh — Verify the read-only shared coding-agent configuration
#
#  USAGE:
#    ./scripts/check-agents.sh
#    source ./scripts/check-agents.sh && check_agents REPO_ROOT USER_DIR
#===============================================================================

set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/lib/common.sh"
source "$SCRIPT_DIR/lib/agent-mcp-servers.sh"

check_agents() {
    local repo_root="$1" user_dir="$2"
    local failed=0 missing_tools=0 entry name url tool
    local base overlay current expected

    for tool in bash jq zsh; do
        if ! command -v "$tool" > /dev/null 2>&1; then
            log_error "Required tool missing: $tool"
            missing_tools=1
        fi
    done
    [[ "$missing_tools" -eq 0 ]] || return 2

    check_file_syntax "$repo_root/dotfiles/link/config/zsh/functions/claude-fable" zsh || failed=1
    check_file_syntax "$repo_root/dotfiles/link/claude/statusline.sh" bash || failed=1

    base="$repo_root/dotfiles/merge/claude/settings.json"
    if ! check_json_object "$base" "Claude settings base"; then
        failed=1
    elif ! check_claude_plugin_structure "$base" "Claude settings base"; then
        failed=1
    fi

    if command -v claude > /dev/null 2>&1; then
        log_step "Checking Claude Code"
        check_agent_link "$user_dir/.claude/CLAUDE.md" "$repo_root/dotfiles/link/claude/CLAUDE.md" "Claude instructions" || failed=1
        check_agent_directory "$user_dir/.claude/agents" "$repo_root/dotfiles/link/claude/agents" "Claude agents" || failed=1

        overlay="$user_dir/.claude/settings.machine.json"
        current="$user_dir/.claude/settings.json"
        if ! check_json_object "$overlay" "Claude settings overlay"; then
            failed=1
        elif ! check_claude_plugin_structure "$overlay" "Claude settings overlay"; then
            failed=1
        fi
        if ! check_json_object "$current" "Generated Claude settings"; then
            failed=1
        elif ! check_claude_plugin_structure "$current" "Generated Claude settings"; then
            failed=1
        elif [[ -f "$overlay" ]] && [[ -f "$base" ]]; then
            # The setup merge owns the complete generated settings file.
            source "$repo_root/scripts/lib/claude-settings.sh"
            if ! expected="$(compose_claude_settings "$base" "$overlay")"; then
                log_error "Could not compose expected Claude settings"
                failed=1
            elif ! cmp -s \
                <(jq -eS . "$current" 2>/dev/null) \
                <(printf '%s' "$expected" | jq -eS . 2>/dev/null); then
                log_error "Generated Claude settings drift from the composed base and overlay; run make set-up/dotfiles"
                failed=1
            else
                log_success "Generated Claude settings match the composed base and overlay"
            fi
        fi

        check_claude_mcp "$user_dir/.claude.json" || failed=1
    else
        log_skip "Claude Code not installed; skipping Claude checks"
    fi

    if command -v codex > /dev/null 2>&1; then
        log_step "Checking Codex"
        check_agent_link "$user_dir/.codex/AGENTS.md" "$repo_root/dotfiles/link/codex/AGENTS.md" "Codex instructions" || failed=1
        check_agent_directory "$user_dir/.codex/agents" "$repo_root/dotfiles/link/codex/agents" "Codex agents" || failed=1
        for entry in "${MCP_HTTP_SERVERS[@]}"; do
            name="${entry%%|*}"; url="${entry#*|}"
            check_codex_mcp "$name" "$url" || failed=1
        done
    else
        log_skip "Codex not installed; skipping Codex checks"
    fi

    if command -v gemini > /dev/null 2>&1; then
        log_step "Checking Gemini"
        check_agent_link "$user_dir/.gemini/GEMINI.md" "$repo_root/dotfiles/link/gemini/GEMINI.md" "Gemini instructions" || failed=1
    else
        log_skip "Gemini not installed; skipping Gemini checks"
    fi

    [[ "$failed" -eq 0 ]]
}

check_file_syntax() {
    local file="$1" shell_name="$2"
    if [[ ! -f "$file" ]]; then log_error "Missing $shell_name script: $(basename "$file")"; return 1; fi
    if "$shell_name" -n "$file" > /dev/null 2>&1; then log_success "$(basename "$file") syntax is valid"; else log_error "$(basename "$file") has invalid $shell_name syntax"; return 1; fi
}

check_json_object() {
    local file="$1" label="$2"
    if [[ ! -f "$file" ]]; then log_error "$label is missing"; return 1; fi
    if jq -e -s 'length == 1 and (.[0] | type == "object")' "$file" > /dev/null 2>&1; then log_success "$label is a JSON object"; else log_error "$label must be a valid JSON object"; return 1; fi
}

check_agent_link() {
    local actual="$1" expected="$2" label="$3"
    if [[ -L "$actual" && "$actual" -ef "$expected" ]]; then log_success "$label link is correct"; else log_error "$label link is missing or points outside this repository; run make set-up/dotfiles"; return 1; fi
}

check_agent_directory() {
    local actual="$1" expected="$2" label="$3"
    if [[ -L "$actual" && "$actual" -ef "$expected" ]]; then log_success "$label directory link is correct"; else log_error "$label directory link is missing or points outside this repository; run make set-up/dotfiles"; return 1; fi
}

check_claude_plugin_structure() {
    local file="$1" label="$2"
    if jq -e '
        (if has("enabledPlugins") then .enabledPlugins | type == "object" else true end) and
        (if has("extraKnownMarketplaces") then .extraKnownMarketplaces | type == "object" else true end)
    ' "$file" > /dev/null 2>&1; then
        log_success "$label plugin inventory has valid object structure"
    else
        log_error "$label plugin inventory fields must be objects when present"
        return 1
    fi
}

check_claude_mcp() {
    local config="$1" entry name url failed=0
    if ! check_json_object "$config" "Claude user configuration"; then return 1; fi
    for entry in "${MCP_HTTP_SERVERS[@]}"; do
        name="${entry%%|*}"; url="${entry#*|}"
        if jq -e --arg name "$name" --arg url "$url" '
            .mcpServers[$name] as $server |
            ($server | type == "object") and
            ($server.type == "http") and
            ($server.url == $url) and ($server.enabled != false)
        ' "$config" > /dev/null 2>&1; then
            log_success "Claude MCP $name is registered"
        else
            log_error "Claude MCP $name is missing, disabled, or has a different URL or transport; inspect it with Claude Code before changing it"
            failed=1
        fi
    done
    [[ "$failed" -eq 0 ]]
}

check_codex_mcp() {
    local name="$1" url="$2" output
    if ! output="$(codex mcp get "$name" --json 2>/dev/null)"; then
        log_error "Codex MCP $name is missing; inspect it with Codex before registering it"
        return 1
    fi
    if printf '%s' "$output" | jq -e -s --arg url "$url" '
        length == 1 and (.[0] | type == "object" and
            (.transport.type == "streamable_http") and (.transport.url == $url) and (.enabled != false))
    ' > /dev/null 2>&1; then
        log_success "Codex MCP $name is registered"
    else
        log_error "Codex MCP $name is disabled or has a different URL or transport; inspect it with Codex before changing it"
        return 1
    fi
}

if [[ "${BASH_SOURCE[0]}" == "$0" ]]; then
    REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
    check_agents "$REPO_ROOT" "$HOME"
    exit $?
fi
