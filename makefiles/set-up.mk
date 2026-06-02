## Migrate from nvm/rbenv/pyenv to mise.
migrate/mise:
	@bash "./scripts/migrate-to-mise.sh"

## Run all setup tasks.
set-up/all: set-up/homebrew set-up/dependencies set-up/dotfiles set-up/idb
	@echo ""
	@echo "✓ All setup tasks complete!"

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
