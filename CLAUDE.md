# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Note: This repository also installs a global Claude configuration at `~/.claude/CLAUDE.md` that applies to all repositories.

## Repository Overview

This is a personal dotfiles repository ("knapsack") for macOS development environments. It manages configuration files for various development tools through a combination of symlinks and copies.

## Key Commands

### Installation
```bash
# Install all dotfiles
make set-up/dotfiles

# After installation, restart your shell or run:
source ~/.zshrc
```

### Working with Configurations

When modifying dotfiles:
- Files in `dotfiles/link/` are symlinked to the home directory - changes here affect the live configuration
- Files in `dotfiles/copy/` are copied during setup - changes require re-running `make set-up/dotfiles`
- Local git configuration goes in `~/.gitconfig_local` (not tracked in repo)
- XDG config directories (like `~/.config/ghostty/`) are symlinked from `dotfiles/link/config/`

## Repository Structure

```
knapsack/
├── README.md             # Main documentation
├── CLAUDE.md             # This file
├── Brewfile              # Homebrew dependencies
├── Makefile              # Main makefile
├── dotfiles/             # Configuration files
│   ├── copy/             # Files to copy (gitconfig_local)
│   └── link/             # Files to symlink
│       ├── config/       # XDG config directory
│       │   └── ghostty/  # Ghostty terminal config
│       ├── claude/       # Claude AI config
│       ├── gitconfig     # Git configuration
│       ├── tmux.conf     # tmux configuration
│       ├── vim/          # vim plugins and config
│       ├── vimrc         # vim configuration
│       └── zshrc         # zsh configuration
├── scripts/              # Utility scripts
│   └── set-up-dotfiles.sh
└── makefiles/            # Makefile includes
    └── set-up.mk
```

## Conventions

### Directory and File Naming
- All directories use lowercase (e.g., `scripts/`, `makefiles/`, `dotfiles/`)
- Scripts use kebab-case with "set-up" as the verb form (e.g., `set-up-dotfiles.sh`)
- Configuration files follow tool conventions (e.g., `Brewfile`, `Makefile`)

### Documentation Standards
All scripts and configuration files follow consistent patterns:
- **File headers**: Simple one-line descriptions with usage for scripts
- **Section headers**: Title Case marked with `--- Section Name ---`
- **Comments**: Complete sentences with periods, explaining why not what
- **Function docs**: Include purpose and argument descriptions

### Theme
The repository uses a custom "Gengar" theme (purple-based) across all terminal applications:
- Primary purple: `#af5fff`
- Bright purple: `#d7afff`
- Background: `#1c1c1c`
- Foreground: `#eeeeee`

## Important Configuration Details

### Shell (zsh)
- Minimal configuration without oh-my-zsh
- Custom PATH management with deduplication via `dedup_path()` function
- Integrates with Homebrew, rbenv (Ruby), and pyenv (Python)
- Sources `~/.profile` if it exists
- Git aliases for common operations

### tmux
- Custom prefix: `C-a` (not default `C-b`)
- Vi-mode bindings for copy mode
- macOS clipboard integration (pbcopy)
- Window splitting: `-` for horizontal, `\` for vertical
- Gengar theme with purple accents

### vim
- Plugin manager: Pathogen
- File explorer: NERDTree (toggle with `F2`)
- Escape mapping: `jk` in insert mode
- Theme: Solarized dark
- Auto-close brackets and quotes
- Relative line numbers in normal mode

### git
- Modular configuration with `~/.gitconfig_local` for machine-specific settings
- Push strategy: simple (push current branch to upstream with same name)
- Custom log formats: `git dag` and `git l`
- Common operation aliases (a, c, cm, s, co, etc.)

### Ghostty Terminal
- Configuration in `~/.config/ghostty/`
- Custom Gengar theme matching tmux/zsh colors
- SF Mono font
- Standard macOS keybindings