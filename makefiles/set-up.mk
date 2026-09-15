## Migrate from nvm/rbenv/pyenv to mise.
migrate/mise:
	@bash "./scripts/migrate-to-mise.sh"

## Run all setup tasks.
set-up/all: set-up/homebrew set-up/dependencies set-up/dotfiles set-up/idb set-up/mcp-servers set-up/agent-skills set-up/codex-routing
	@echo ""
	@echo "✓ All setup tasks complete!"

## Install shared agent skills for Codex via the skills CLI.
set-up/agent-skills:
	@bash "./scripts/set-up-agent-skills.sh"

## Install dependencies from Brewfile.
set-up/dependencies:
	@bash "./scripts/set-up-dependencies.sh"

## Set up the dotfiles on the system.
set-up/dotfiles:
	@bash "./scripts/set-up-dotfiles.sh"

## Install Homebrew package manager.
set-up/homebrew:
	@bash "./scripts/set-up-homebrew.sh"

## Install Facebook idb companion and client.
set-up/idb:
	@bash "./scripts/set-up-idb.sh"

## Create local functions directory for machine-specific functions.
set-up/local-functions:
	@bash "./scripts/set-up-local-functions.sh"

## Register shared MCP servers with Claude Code and Codex.
set-up/mcp-servers:
	@bash "./scripts/set-up-mcp-servers.sh"

## Register native Codex routing profiles without enabling or trusting hooks.
set-up/codex-routing: set-up/dotfiles
	@python3 "./scripts/set-up-codex-routing.py"

## Tune macOS for heavy parallel development (opt-in; requires sudo).
set-up/performance:
	@bash "./scripts/set-up-performance.sh"
