# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Note: This repository also installs a global Claude configuration at `~/.claude/CLAUDE.md` that applies to all repositories.

## Repository Overview

This is a personal dotfiles repository ("knapsack") for macOS development environments. It manages configuration files for various development tools through a combination of symlinks and copies.

## Key Commands

### Installation
```bash
# Install all dotfiles
cd dotfiles && bash setup.sh

# After installation, restart your shell or run:
source ~/.zshrc
```

### Working with Configurations

When modifying dotfiles:
- Files in `dotfiles/link/` are symlinked to the home directory - changes here affect the live configuration
- Files in `dotfiles/copy/` are copied during setup - changes require re-running setup.sh
- Local git configuration goes in `~/.gitconfig_local` (not tracked in repo)

## Architecture

The repository follows a modular structure:

- **dotfiles/**: Core configuration files split into `link/` (symlinked) and `copy/` (copied) directories
- **applications/**: IDE and application-specific themes/settings (IntelliJ IDEA, iTerm2, Xcode)
- **scripts/**: Utility scripts (currently contains note-taking utilities)
- **external/**: Third-party resources (powerline fonts)

The `dotfiles/setup.sh` script handles installation by:
1. Creating symlinks for files in `dotfiles/link/` to `~/.<filename>`
2. Copying files from `dotfiles/copy/` to `~/.<filename>`
3. Setting up the local gitconfig file if it doesn't exist

## Important Configuration Details

### Shell (zsh)
- Uses oh-my-zsh with robbyrussell theme
- Custom PATH management with deduplication via `dedup_path()` function
- Integrates with Homebrew, rbenv (Ruby), and pyenv (Python)
- Sources `~/.profile` if it exists

### tmux
- Custom prefix: `C-a` (not default `C-b`)
- Vi-mode bindings for copy mode
- macOS clipboard integration
- Window splitting: `|` for vertical, `-` for horizontal

### vim
- Plugin manager: Pathogen
- File explorer: NERDTree (toggle with `<leader>n`)
- Escape mapping: `jk` in insert mode
- Theme: Solarized dark

### git
- Modular configuration with `~/.gitconfig_local` for machine-specific settings
- Push strategy: simple (push current branch to upstream with same name)
- Notable aliases defined in gitconfig