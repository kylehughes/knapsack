# knapsack

Personal dotfiles and development environment configuration for macOS.

## Installation

```sh
# Clone repository
cd ~ && git clone git@github.com:kylehughes/knapsack.git
cd ~/knapsack

# Run all setup tasks
make set-up/all
```

Or run individual setup tasks:

```sh
make set-up/homebrew        # Install Homebrew
make set-up/dependencies    # Install dependencies from Brewfile
make set-up/submodules      # Initialize git submodules
make set-up/dotfiles        # Install dotfiles
make set-up/local-functions # Create local functions directory
```

## Structure

### Dotfiles

Configuration files managed by `make set-up/dotfiles`:

| Configuration | Type | Description |
| --- | --- | --- |
| `claude/CLAUDE.md` | Symlink | Claude AI configuration. |
| `config/ghostty/*` | Symlink | Ghostty terminal configuration. |
| `config/zsh/functions/*` | Symlink | Custom shell functions. |
| `gitconfig` | Symlink | Global git configuration. |
| `gitconfig_local` | Copy | Local git overrides (not tracked). |
| `tmux.conf` | Symlink | tmux configuration. |
| `vim/*` | Symlink | vim configuration and plugins. |
| `vimrc` | Symlink | vim configuration. |
| `zshrc` | Symlink | zsh shell configuration. |

### Shell Functions

Custom zsh functions for common workflows, autoloaded from `~/.config/zsh/functions/`:

#### Git Workflow Functions

| Function | Description | Usage |
| --- | --- | --- |
| `git-add-amend-force-push` | Stage all changes, amend commit, and force push. | `git-add-amend-force-push` |
| `git-add-commit` | Stage all changes and commit with message. | `git-add-commit "message"` |
| `git-fetch-pull` | Fetch remote changes and pull with rebase. | `git-fetch-pull` |
| `git-log-dag` | Show detailed commit graph with author info. | `git-log-dag [options]` |
| `git-log-graph` | Show commit history as decorated graph. | `git-log-graph [options]` |
| `git-log-pretty` | Show formatted log with details on one line. | `git-log-pretty [options]` |
| `git-push-upstream` | Push current branch and set upstream tracking. | `git-push-upstream` |
| `git-status-diff` | Show status and diff for review. | `git-status-diff` |

Functions follow the `tool-action` naming convention for clarity and tab completion support.

#### Local Functions

Machine-specific functions can be placed in `~/.config/zsh/functions-local/` (not tracked in git):

```sh
# Create local functions directory
make set-up/local-functions

# Add a local function
echo '#!/usr/bin/env zsh
# my-local-function - Description here.
echo "This function only exists on this machine"' > ~/.config/zsh/functions-local/my-local-function
chmod +x ~/.config/zsh/functions-local/my-local-function
```

Local functions are autoloaded just like tracked functions but remain private to each machine.

## Dependencies

Managed via `Brewfile`:

```sh
brew bundle install    # Install all dependencies
brew bundle check      # Check for missing packages
brew bundle cleanup    # Remove unlisted packages
```

## Development

### Documentation Standards

All scripts and configuration files follow consistent documentation patterns:

- **File headers**: Simple one-line descriptions with usage information for scripts.
- **Section headers**: Title Case sections marked with `--- Section Name ---`.
- **Comments**: Complete sentences with periods, explaining why not what.
- **No decorations**: Clean, readable formatting without excessive separators.

## Theme

A Gengar-inspired purple theme consistent across all terminal applications:

| Color | Hex | Usage |
| --- | --- | --- |
| Background | `#1c1c1c` | Terminal background. |
| Foreground | `#eeeeee` | Primary text. |
| Purple | `#af5fff` | Status bars, borders. |
| Bright Purple | `#d7afff` | Active elements. |
| Grey | `#444444` | Inactive elements. |