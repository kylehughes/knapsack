## Install Homebrew package manager.
set-up/homebrew:
	@bash "./scripts/set-up-homebrew.sh"

## Install dependencies from Brewfile.
set-up/dependencies:
	@bash "./scripts/set-up-dependencies.sh"

## Initialize and update git submodules.
set-up/submodules:
	@bash "./scripts/set-up-submodules.sh"

## Set up the dotfiles on the system.
set-up/dotfiles:
	@bash "./scripts/set-up-dotfiles.sh"

## Run all setup tasks.
set-up/all: set-up/homebrew set-up/dependencies set-up/submodules set-up/dotfiles
	@echo ""
	@echo "✓ All setup tasks complete!"