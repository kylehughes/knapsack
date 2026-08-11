#!/usr/bin/env bash
#===============================================================================
#  set-up-agent-skills.sh — Install shared agent skills for Codex via the skills CLI
#
#  USAGE:
#    ./scripts/set-up-agent-skills.sh
#
#  Installs the Agent Skills (agentskills.io) that Knapsack wants available for
#  Codex, using the skills CLI (https://github.com/vercel-labs/skills, invoked as
#  `npx skills`) to manage ~/.agents/skills as a package manager rather than
#  having this repository track the installed artifacts. Claude Code consumes
#  the same content through its plugin system, declared in the merged settings
#  base. Re-running is safe: the skills CLI reinstalls/updates skills in place.
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

# --- Shared Agent Skills ---
#
# Skills to install for Codex, as "repo|skill" pairs.

AGENT_SKILLS=(
    # Claude Code consumes the same repository as the writing-prose-like-a-human
    # plugin, declared in the merged settings base; keep the two in sync.
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
