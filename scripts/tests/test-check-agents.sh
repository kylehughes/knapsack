#!/bin/bash
# test-check-agents.sh — Isolated tests for scripts/check-agents.sh.

set -eu

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
FIXTURE_ROOT="$(mktemp -d "${TMPDIR:-/tmp}/check-agents.XXXXXX")"

cleanup() { rm -rf "$FIXTURE_ROOT"; }
trap cleanup EXIT HUP INT TERM

fail() { echo "FAIL: $*" >&2; exit 1; }
expect_status() {
    local expected="$1"; shift
    set +e
    "$@" > "$FIXTURE_ROOT/output" 2>&1
    local actual=$?
    set -e
    [[ "$actual" -eq "$expected" ]] || { cat "$FIXTURE_ROOT/output" >&2; fail "expected exit $expected, got $actual"; }
}
expect_output() { grep -F "$1" "$FIXTURE_ROOT/output" > /dev/null || fail "missing diagnostic: $1"; }
snapshot() { find "$FIXTURE_ROOT/repo" "$FIXTURE_ROOT/user-dir" "$FIXTURE_ROOT/temp" -type f -exec shasum {} \; | sort; }

make_repo() {
    local repo="$FIXTURE_ROOT/repo"
    mkdir -p "$repo/dotfiles/shared/claude/agents" "$repo/dotfiles/shared/codex/agents" \
        "$repo/dotfiles/shared/gemini" "$repo/dotfiles/shared/config/zsh/functions" \
        "$repo/dotfiles/merge/claude" "$repo/scripts/lib"
    printf 'managed profile\n' > "$repo/dotfiles/shared/codex/agents/knapsack-test.toml"
    printf 'claude instructions\n' > "$repo/dotfiles/shared/claude/CLAUDE.md"
    chmod 644 "$repo/dotfiles/shared/claude/CLAUDE.md"
    ln -s ../claude/CLAUDE.md "$repo/dotfiles/shared/codex/AGENTS.md"
    ln -s ../claude/CLAUDE.md "$repo/dotfiles/shared/gemini/GEMINI.md"
    printf '#!/usr/bin/env zsh\ntrue\n' > "$repo/dotfiles/shared/config/zsh/functions/claude-fable"
    printf '#!/bin/bash\ntrue\n' > "$repo/dotfiles/shared/claude/statusline.sh"
    printf '{"setting":"base","enabledPlugins":{"shared":true},"extraKnownMarketplaces":{"shared":{}}}\n' > "$repo/dotfiles/merge/claude/settings.json"
    ln -s "$PROJECT_ROOT/scripts/lib/claude-settings.sh" "$repo/scripts/lib/claude-settings.sh"
}

make_user_dir() {
    local repo="$FIXTURE_ROOT/repo" user_dir="$FIXTURE_ROOT/user-dir"
    mkdir -p "$user_dir/.claude" "$user_dir/.codex" "$user_dir/.gemini" "$FIXTURE_ROOT/temp"
    cp -p "$repo/dotfiles/shared/claude/CLAUDE.md" "$user_dir/.claude/CLAUDE.md"
    cp -p "$repo/dotfiles/shared/claude/statusline.sh" "$user_dir/.claude/statusline.sh"
    cp -Rp "$repo/dotfiles/shared/claude/agents" "$user_dir/.claude/agents"
    cp -Lp "$repo/dotfiles/shared/codex/AGENTS.md" "$user_dir/.codex/AGENTS.md"
    cp -Rp "$repo/dotfiles/shared/codex/agents" "$user_dir/.codex/agents"
    cp -Lp "$repo/dotfiles/shared/gemini/GEMINI.md" "$user_dir/.gemini/GEMINI.md"
    printf '{"machine":"value","enabledPlugins":{"shared":false},"extraKnownMarketplaces":{"local":{}}}\n' > "$user_dir/.claude/settings.machine.json"
    printf '{"setting":"base","machine":"value","enabledPlugins":{"shared":false},"extraKnownMarketplaces":{"shared":{},"local":{}}}\n' > "$user_dir/.claude/settings.json"
    printf '{"mcpServers":{"sosumi":{"type":"http","url":"https://sosumi.ai/mcp","enabled":true}}}\n' > "$user_dir/.claude.json"
}

make_bin() {
    local bin="$FIXTURE_ROOT/bin"
    mkdir -p "$bin"
    for tool in bash jq zsh basename cat cmp dirname stat; do
        [[ -e "$bin/$tool" ]] || ln -s "$(command -v "$tool")" "$bin/$tool"
    done
    cat > "$bin/claude" <<'EOF'
#!/bin/sh
exit 0
EOF
    cat > "$bin/gemini" <<'EOF'
#!/bin/sh
exit 0
EOF
    cat > "$bin/codex" <<'EOF'
#!/bin/sh
if [ "$1" = mcp ] && [ "$2" = get ] && [ "$4" = --json ]; then cat "$CODEX_MCP_FIXTURE"; exit 0; fi
exit 1
EOF
    chmod +x "$bin/claude" "$bin/codex" "$bin/gemini"
    printf '{"enabled":true,"transport":{"type":"streamable_http","url":"https://sosumi.ai/mcp"}}\n' > "$FIXTURE_ROOT/codex.json"
}

run_check() {
    PATH="$FIXTURE_ROOT/bin" TMPDIR="$FIXTURE_ROOT/temp" CODEX_MCP_FIXTURE="$FIXTURE_ROOT/codex.json" \
        /bin/bash -c 'source "$1"; check_agents "$2" "$3"' check "$PROJECT_ROOT/scripts/check-agents.sh" "$FIXTURE_ROOT/repo" "$FIXTURE_ROOT/user-dir"
}

make_repo
make_user_dir
make_bin
# Canonical instruction aliases install as regular files with the target mode.
[[ ! -L "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md" ]] || fail "Codex fixture copy is a symlink"
[[ ! -L "$FIXTURE_ROOT/user-dir/.gemini/GEMINI.md" ]] || fail "Gemini fixture copy is a symlink"
before="$(snapshot)"
expect_status 0 run_check
expect_output "Codex instructions copy is correct"
expect_output "Gemini instructions copy is correct"
[[ "$before" = "$(snapshot)" ]] || fail "healthy check changed fixture files"

# The tracked base uses the same plugin-field shape rules.
printf '{"setting":"base","enabledPlugins":false}\n' > "$FIXTURE_ROOT/repo/dotfiles/merge/claude/settings.json"
expect_status 1 run_check
expect_output "Claude settings base plugin inventory fields must be objects"
printf '{"setting":"base","enabledPlugins":{"shared":true},"extraKnownMarketplaces":{"shared":{}}}\n' > "$FIXTURE_ROOT/repo/dotfiles/merge/claude/settings.json"

# Plugin declarations in the overlay override base values and belong in current.
printf '{"machine":"value","enabledPlugins":{"shared":false},"extraKnownMarketplaces":{"local":{}}}\n' > "$FIXTURE_ROOT/user-dir/.claude/settings.machine.json"
expect_status 0 run_check
expect_output "Generated Claude settings match"

# Removing declared plugin fields from current is generated-settings drift.
printf '{"setting":"base","machine":"value"}\n' > "$FIXTURE_ROOT/user-dir/.claude/settings.json"
expect_status 1 run_check
expect_output "Generated Claude settings drift"
printf '{"setting":"base","machine":"value","enabledPlugins":{"shared":false},"extraKnownMarketplaces":{"shared":{},"local":{}}}\n' > "$FIXTURE_ROOT/user-dir/.claude/settings.json"

# A successful CLI command must still return one complete registration.
: > "$FIXTURE_ROOT/codex.json"
expect_status 1 run_check
expect_output "Codex MCP sosumi is disabled or has a different URL or transport"
printf '{"enabled":true,"transport":{"type":"streamable_http","url":"https://sosumi.ai/mcp"}}\n' > "$FIXTURE_ROOT/codex.json"

rm "$FIXTURE_ROOT/bin/zsh"
expect_status 2 run_check
expect_output "Required tool missing: zsh"
make_bin

rm "$FIXTURE_ROOT/bin/claude" "$FIXTURE_ROOT/bin/codex" "$FIXTURE_ROOT/bin/gemini"
expect_status 0 run_check
make_bin

printf '{"enabled":false,"transport":{"type":"streamable_http","url":"https://sosumi.ai/mcp"}}\n' > "$FIXTURE_ROOT/codex.json"
expect_status 1 run_check
expect_output "Codex MCP sosumi is disabled"
printf '{"enabled":true,"transport":{"type":"streamable_http","url":"https://sosumi.ai/mcp"}}\n' > "$FIXTURE_ROOT/codex.json"
printf '{"mcpServers":{"sosumi":{"type":"http","url":"PRIVATE_URL_SENTINEL","enabled":true}}}\n' > "$FIXTURE_ROOT/user-dir/.claude.json"
expect_status 1 run_check
expect_output "Claude MCP sosumi is missing"
if grep -q 'PRIVATE_URL_SENTINEL' "$FIXTURE_ROOT/output"; then fail "checker exposed an MCP URL"; fi
printf '{"mcpServers":{"sosumi":{"type":"http","url":"https://sosumi.ai/mcp","enabled":true}}}\n' > "$FIXTURE_ROOT/user-dir/.claude.json"

rm "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md"
printf 'not a link\n' > "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md"
expect_status 1 run_check
expect_output "Codex instructions copy is missing or differs"
rm "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md"
ln -s "$FIXTURE_ROOT/repo/dotfiles/shared/codex/AGENTS.md" "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md"
expect_status 1 run_check
expect_output "Codex instructions must be an isolated copy"
rm "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md"
cp -Lp "$FIXTURE_ROOT/repo/dotfiles/shared/codex/AGENTS.md" "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md"

# Copies retain executable bits and only managed profile names are checked.
chmod +x "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md"
expect_status 1 run_check
expect_output "Codex instructions executable bits differ"
chmod -x "$FIXTURE_ROOT/user-dir/.codex/AGENTS.md"
# Executable source files must retain their executable bits in the installed copy.
chmod +x "$FIXTURE_ROOT/repo/dotfiles/shared/claude/statusline.sh"
expect_status 1 run_check
expect_output "Claude statusline executable bits differ"
chmod +x "$FIXTURE_ROOT/user-dir/.claude/statusline.sh"
expect_status 0 run_check
chmod -x "$FIXTURE_ROOT/repo/dotfiles/shared/claude/statusline.sh" "$FIXTURE_ROOT/user-dir/.claude/statusline.sh"
printf 'local profile\n' > "$FIXTURE_ROOT/user-dir/.codex/agents/local.toml"
expect_status 0 run_check
mv "$FIXTURE_ROOT/user-dir/.codex/agents" "$FIXTURE_ROOT/user-dir/.codex/agents-saved"
ln -s "$FIXTURE_ROOT/repo/dotfiles/shared/codex/agents" "$FIXTURE_ROOT/user-dir/.codex/agents"
expect_status 1 run_check
expect_output "Codex agents must be an isolated copy"
rm "$FIXTURE_ROOT/user-dir/.codex/agents"
mv "$FIXTURE_ROOT/user-dir/.codex/agents-saved" "$FIXTURE_ROOT/user-dir/.codex/agents"
printf 'altered profile\n' > "$FIXTURE_ROOT/user-dir/.codex/agents/knapsack-test.toml"
expect_status 1 run_check
expect_output "Codex agents knapsack-test.toml copy is missing or differs"
cp -p "$FIXTURE_ROOT/repo/dotfiles/shared/codex/agents/knapsack-test.toml" "$FIXTURE_ROOT/user-dir/.codex/agents/knapsack-test.toml"

printf '{"sentinel":"DO_NOT_PRINT_SECRET"' > "$FIXTURE_ROOT/user-dir/.claude/settings.json"
expect_status 1 run_check
expect_output "Generated Claude settings must be a valid JSON object"
if grep -q 'DO_NOT_PRINT_SECRET' "$FIXTURE_ROOT/output"; then fail "checker exposed malformed JSON content"; fi
printf '{"setting":"base","machine":"value"}\n{"extra":true}\n' > "$FIXTURE_ROOT/user-dir/.claude/settings.json"
expect_status 1 run_check
expect_output "Generated Claude settings must be a valid JSON object"
printf '{"enabledPlugins":false}\n' > "$FIXTURE_ROOT/user-dir/.claude/settings.machine.json"
expect_status 1 run_check
expect_output "Claude settings overlay plugin inventory fields must be objects"
printf '{"machine":"value","enabledPlugins":{"shared":false},"extraKnownMarketplaces":{"local":{}}}\n' > "$FIXTURE_ROOT/user-dir/.claude/settings.machine.json"
printf '{"setting":"drift","machine":"value","enabledPlugins":{"shared":false},"extraKnownMarketplaces":{"shared":{},"local":{}}}\n' > "$FIXTURE_ROOT/user-dir/.claude/settings.json"
expect_status 1 run_check
expect_output "Generated Claude settings drift"

echo "PASS: check-agents fixtures"
