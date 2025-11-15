# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code across all repositories.

## Skills for Context Discovery

Skills often contain valuable contextual information about the project you're working on. Consider using them to discover project-specific knowledge, established patterns, and domain expertise that may not be immediately apparent from the codebase alone. They're particularly useful when you need specialized knowledge or want to ensure consistency with existing patterns.

## Git Commit Guidelines

When creating git commits:
1. Analyze the repository's git history first to understand the commit style
2. Write commits in the user's voice and style
3. Match the typical commit message density and format used in the repository
4. Never credit yourself, Claude, or AI assistance in commit messages
5. Make commits appear as if written directly by the user

To analyze commit style, run:
```bash
git log --oneline -20  # Recent commit style and density
git log -5             # Detailed recent commits
```

Focus on:
- Message length and detail level
- Capitalization patterns
- Use of imperative mood vs past tense
- Common phrases or conventions
- Punctuation usage

## Available Environment

This machine has been set up with the Knapsack dotfiles project, providing the following tools and configurations:

### Terminal Environment
- **Shell**: zsh with custom configuration (no oh-my-zsh)
- **Terminal Multiplexer**: tmux with prefix `C-a` and vim-style navigation
- **Terminal Emulator**: Ghostty with custom Gengar theme (purple-based)
- **Editor**: vim with Pathogen, NERDTree (F2), and Solarized dark theme

### Key Tools Available
- **ripgrep** (`rg`): Fast file content search (preferred over grep/find)
- **jq**: JSON processing and manipulation
- **ffmpeg**: Media processing with custom `ffmpeg-reduce-size` function
- **git**: Enhanced with custom aliases and workflow functions
- **pyenv**: Python version management
- **rbenv**: Ruby version management
- **node/nvm**: Node.js and version management
- **poetry**: Python package management
- **repomix**: Pack repository contents for AI consumption

### Git Enhancements

#### Aliases (use with `git` command)
- `dag`: Detailed commit graph
- `l`: Pretty one-line log
- `a`, `aa`: Add files
- `c`, `cm`, `ca`: Commit variations
- `s`: Status
- `co`, `cob`: Checkout operations
- `pr`: Pull with rebase

#### Custom Functions (available as shell commands)
- `git-add-commit`: Stage all and commit with message
- `git-add-amend-force-push`: Common PR update workflow
- `git-fetch-pull`: Fetch and pull with rebase
- `git-log-dag`, `git-log-graph`, `git-log-pretty`: Various log views
- `git-push-upstream`: Push and set upstream tracking
- `git-status-diff`: Review changes before committing

### Shell Aliases
- **Git shortcuts**: `g`, `ga`, `gaa`, `gb`, `gc`, `gca`, `gcam`, `gco`, `gd`, `gf`, `gl`, `glog`, `gp`, `gr`, `gst`
- **Directory listing**: `ll`, `la`, `l`

### Local Customization
- **Local functions**: Place machine-specific functions in `~/.config/zsh/functions-local/`
- **Local git config**: Machine-specific git settings in `~/.gitconfig_local`
- Both directories are gitignored and persist across updates

### Important Notes
- Functions follow `tool-action` naming convention for consistency
- All configurations use XDG Base Directory specification
- Consistent Gengar theme (purple) across all terminal applications
- PATH includes ~/bin, Homebrew, and language version managers
