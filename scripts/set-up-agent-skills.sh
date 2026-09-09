#!/usr/bin/env bash
#===============================================================================
#  set-up-agent-skills.sh — Install Knapsack's standalone Codex writing skill
#
#  USAGE:
#    ./scripts/set-up-agent-skills.sh
#
#  Installs the standalone Codex writing-prose-like-a-human skill through the
#  Agent Skills CLI (https://github.com/vercel-labs/skills, invoked as `npx
#  skills`). The corresponding Claude Code plugin is declared in Knapsack's
#  merged settings base; Codex configures this separate skill through the CLI.
#  Re-running is safe: the skills CLI reinstalls or updates this skill in place.
#
#  EXIT CODES:
#    0  success
#    2  missing dependency (npx)
#
#  AUTHOR:      Kyle Hughes <kyle@kylehugh.es>
#  LICENSE:     MIT
#===============================================================================

set -euo pipefail

source "$(dirname "$0")/lib/common.sh"

# --- Explicitly Managed Codex Skill ---
#
# The Codex skill to install, as a "repo|skill" pair.

AGENT_SKILLS=(
    # Keep this separately configured Codex skill aligned with Claude Code's
    # corresponding plugin declaration in the merged settings base.
    "kylehughes/writing-prose-like-a-human-for-agents|writing-prose-like-a-human"
)

# --- Main ---

log_step "Installing shared agent skills"

if ! command -v npx &> /dev/null; then
    log_error "npx is required for the skills CLI; install node via mise or Homebrew"
    exit 2
fi

# The repository symlinked ~/.agents/skills to a tracked directory until August
# 2026; a machine that just pulled still has that (now dangling) link, and the
# skills CLI needs a real directory to manage.
if [[ -L "$HOME/.agents/skills" ]]; then
    rm "$HOME/.agents/skills"
    log_skip "Removed stale ~/.agents/skills symlink from the old tracked-directory setup"
fi

for entry in "${AGENT_SKILLS[@]}"; do
    repo="${entry%%|*}"
    skill="${entry#*|}"

    npx -y skills add "$repo" -g -a codex -s "$skill" -y
    log_success "Codex: installed $skill from $repo"
done

log_success "Agent skill setup complete"
