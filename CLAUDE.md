# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Note: This repository also installs a global Claude configuration at `~/.claude/CLAUDE.md` that applies to all repositories.

## Repository Overview

This is a personal dotfiles repository ("Knapsack") for macOS development environments. It manages configuration files for various development tools through a combination of symlinks and copies.

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
Knapsack/
├── README.md             # Main documentation
├── CLAUDE.md             # This file
├── GEMINI.md             # Symlink → CLAUDE.md (Gemini CLI)
├── AGENTS.md             # Symlink → CLAUDE.md (Codex CLI)
├── Brewfile              # Homebrew dependencies
├── Makefile              # Main makefile
├── dotfiles/             # Configuration files
│   ├── copy/             # Files to copy (gitconfig_local)
│   └── link/             # Files to symlink
│       ├── config/       # XDG config directory
│       │   └── ghostty/  # Ghostty terminal config
│       ├── agents/       # Shared agent skills (symlinks → claude/)
│       ├── claude/       # Claude AI config (source of truth)
│       ├── codex/        # Codex CLI config (symlinks → claude/)
│       ├── gemini/       # Gemini CLI config (symlinks → claude/)
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

#### Script Header Template
For more complex scripts requiring detailed documentation, use this extended header format:

```bash
#!/usr/bin/env bash
#===============================================================================
#  script-name — Brief description
#
#  USAGE:
#    Detailed usage instructions
#
#  OPTIONS:
#    -h, --help     Show this help message
#    -v, --verbose  Enable verbose output
#
#  REQUIREMENTS:
#    bash ≥ 3.x, git, other dependencies
#
#  EXIT CODES:
#    0  success
#    1  usage error (bad flags, etc.)
#    2  missing dependency
#    >2 script-specific failures
#
#  AUTHOR:      Kyle Hughes <kyle@kylehugh.es>
#  LICENSE:     MIT
#===============================================================================
```

This extended format is recommended for:
- Scripts with command-line options
- Scripts that may fail in multiple ways
- Scripts intended for wider distribution
- Git hooks and other automated scripts

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
- Custom functions autoloaded from `~/.config/zsh/functions/`
- Local functions supported via `~/.config/zsh/functions-local/` (not tracked)

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

## Shell Functions

The repository implements custom zsh functions using XDG Base Directory specification with autoloading for performance. Functions are stored in `dotfiles/link/config/zsh/functions/` and autoloaded via `$fpath`.

### Design Decisions

1. **XDG Compliance**: Functions live in `~/.config/zsh/functions/` following modern Unix conventions
2. **Autoloading**: Functions are lazy-loaded using zsh's autoload mechanism for faster shell startup
3. **Naming Convention**: Functions use `tool-action` format (e.g., `git-add-commit`) for:
   - Clear purpose identification
   - Logical tab completion grouping
   - Avoiding naming conflicts
4. **Documentation**: Each function follows repository standards with header, usage, and inline comments

### Available Functions

#### Git Workflows
- `git-add-amend-force-push` - Common PR workflow: stage all, amend, force push
- `git-add-commit` - Stage all changes and commit with message
- `git-fetch-pull` - Fetch and pull with rebase to maintain linear history
- `git-log-dag` - Detailed commit graph (replaces `git dag` alias)
- `git-log-graph` - One-line decorated graph (replaces `glog` alias)
- `git-log-pretty` - Formatted one-line log (replaces `git l` alias)
- `git-push-upstream` - Push and set upstream tracking for new branches
- `git-status-diff` - Review changes before committing

### Adding New Functions

1. Create executable file in `dotfiles/link/config/zsh/functions/`:
   ```bash
   #!/usr/bin/env zsh
   # tool-action - Brief description.
   # Usage: tool-action [arguments]
   
   # Implementation with comments explaining why.
   ```

2. Make executable: `chmod +x dotfiles/link/config/zsh/functions/tool-action`

3. Functions are automatically available after `make set-up/dotfiles` and shell restart

### Local Functions

For machine-specific functions that shouldn't be tracked in git:

1. **Setup**: Run `make set-up/local-functions` to create the directory structure
2. **Location**: Functions live in `~/.config/zsh/functions-local/`
3. **Priority**: Local functions are loaded after tracked functions, so they can override
4. **Usage**: Same as tracked functions - create executable files following naming conventions

Example use cases:
- Work-specific VPN or SSH shortcuts
- Machine-specific build scripts
- Local development server commands
- Personal aliases that shouldn't be shared
