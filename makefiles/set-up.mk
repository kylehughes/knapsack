## Migrate from nvm/rbenv/pyenv to mise.
migrate/mise:
	@bash "./scripts/migrate-to-mise.sh"

## Run all setup tasks.
set-up/all: set-up/homebrew set-up/dependencies set-up/dotfiles set-up/orca set-up/idb set-up/mcp-servers set-up/agent-skills set-up/codex-routing set-up/repository-hook
	@echo ""
	@echo "✓ All setup tasks complete!"

## Install shared agent skills for Codex via the skills CLI.
set-up/agent-skills:
	@bash "./scripts/set-up-agent-skills.sh"

## Install dependencies from Brewfile.
set-up/dependencies:
	@bash "./scripts/set-up-dependencies.sh"

## Install independent dotfile copies, preserving local changes.
set-up/dotfiles:
	@bash "./scripts/set-up-dotfiles.sh"

## Install the repository's staged-source guard without replacing custom hooks.
set-up/repository-hook:
	@python3 -B "./scripts/set-up-repository-hook.py"

## Install Homebrew package manager.
set-up/homebrew:
	@bash "./scripts/set-up-homebrew.sh"

## Install Facebook idb companion and client.
set-up/idb:
	@bash "./scripts/set-up-idb.sh"

## Patch Orca's live settings from the tracked base and machine overlay.
set-up/orca:
	@bash "./scripts/set-up-orca-settings.sh"

## Create local functions directory for machine-specific functions.
set-up/local-functions:
	@bash "./scripts/set-up-local-functions.sh"

## Register shared MCP servers with Claude Code and Codex.
set-up/mcp-servers:
	@bash "./scripts/set-up-mcp-servers.sh"

## Register native Codex routing profiles without enabling or trusting hooks.
set-up/codex-routing: set-up/dotfiles
	@python3 -B "./scripts/set-up-codex-routing.py"

## Tune macOS for heavy parallel development (opt-in; requires sudo).
set-up/performance:
	@bash "./scripts/set-up-performance.sh"
