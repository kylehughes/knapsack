#!/usr/bin/env bash
#===============================================================================
#  set-up-mcp-servers.sh — Register shared MCP servers with Claude Code and Codex
#
#  USAGE:
#    ./scripts/set-up-mcp-servers.sh
#
#  Registers the MCP servers that Knapsack wants available in every project, for
#  each installed agent CLI. Both tools keep MCP configuration inside large,
#  stateful, secret-bearing files (~/.claude.json, ~/.codex/config.toml), so we
#  register through each tool's official CLI rather than tracking those files in
#  the repo. Re-running is safe: servers already present are left untouched.
#
#  EXIT CODES:
#    0  success (a missing agent CLI is skipped, not an error)
#    1  a registration command failed
#
#  AUTHOR:      Kyle Hughes <kyle@kylehugh.es>
#  LICENSE:     MIT
#===============================================================================

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# --- Shared MCP Servers ---
#
# Streamable HTTP MCP servers to register for every agent, as "name|url" pairs.
# Keep these public and secret-free; anything needing a token or per-machine
# value belongs in machine-local config, not in this tracked list.

MCP_HTTP_SERVERS=(
    # sosumi.ai renders Apple's JavaScript-only developer documentation into
    # Markdown and exposes search/fetch/transcript tools. The Apple Documentation
    # section of CLAUDE.md documents the URL-rewriting fallback for agents without
    # this server.
    "sosumi|https://sosumi.ai/mcp"
)

# --- Functions ---

command_exists() {
    command -v "$1" &> /dev/null
}

# Register one streamable HTTP MCP server with Claude Code at user scope so it is
# available across every project. Skips servers that are already registered.
register_claude_server() {
    local name="$1" url="$2"

    if claude mcp get "$name" &> /dev/null; then
        log_skip "Claude Code: $name already registered"
        return
    fi

    claude mcp add --transport http --scope user "$name" "$url"
    log_success "Claude Code: registered $name"
}

# Register one streamable HTTP MCP server with Codex. Skips servers that are
# already registered.
register_codex_server() {
    local name="$1" url="$2"

    if codex mcp get "$name" &> /dev/null; then
        log_skip "Codex: $name already registered"
        return
    fi

    codex mcp add "$name" --url "$url"
    log_success "Codex: registered $name"
}

# --- Main ---

log_step "Registering shared MCP servers"

if ! command_exists claude && ! command_exists codex; then
    log_skip "Neither Claude Code nor Codex is installed; nothing to register"
    exit 0
fi

for entry in "${MCP_HTTP_SERVERS[@]}"; do
    name="${entry%%|*}"
    url="${entry#*|}"

    if command_exists claude; then
        register_claude_server "$name" "$url"
    else
        log_skip "Claude Code not installed; skipping $name"
    fi

    if command_exists codex; then
        register_codex_server "$name" "$url"
    else
        log_skip "Codex not installed; skipping $name"
    fi
done

log_success "MCP server setup complete"
