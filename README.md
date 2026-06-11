# Knapsack

Kyle Hughes's dotfiles and development environment configuration for macOS.

## Installation

```sh
# Clone repository
cd ~ && git clone git@github.com:kylehughes/knapsack.git Knapsack
cd ~/Knapsack

# Run all setup tasks
make set-up/all
```

Or run individual setup tasks:

```sh
make set-up/homebrew        # Install Homebrew
make set-up/dependencies    # Install dependencies from Brewfile
make set-up/dotfiles        # Install dotfiles
make set-up/idb             # Install Facebook idb companion and client
make set-up/local-functions # Create local functions directory
```

## Structure

### Dotfiles

Configuration files managed by `make set-up/dotfiles`. Symlinked files take
effect immediately when edited in the repository; copied files require
re-running the setup task. If a symlink destination is already a real
directory, the setup script backs it up to `<path>.backup.<timestamp>` before
linking.

| Configuration | Type | Description |
| --- | --- | --- |
| `claude/CLAUDE.md` | Symlink | Global instructions for all AI agents. |
| `claude/settings.json` | Symlink | Claude Code settings (model, permissions, hooks, plugins). |
| `claude/statusline.sh` | Symlink | Claude Code status line script. |
| `claude/agents/*`, `claude/skills/*` | Symlink | Custom subagents and skills. |
| `agents/`, `codex/`, `gemini/` | Symlink | Re-export the Claude configuration to Codex CLI, Gemini CLI, and the agentskills.io path. |
| `config/ghostty/*` | Symlink | Ghostty terminal configuration and theme. |
| `config/mise/*` | Symlink | mise tool version pins (node, ruby). |
| `config/zsh/functions/*` | Symlink | Custom shell functions. |
| `gitconfig` | Symlink | Global git configuration. |
| `gitconfig_local` | Copy | Machine-specific git settings, including user identity (not tracked). |
| `gitignore_global` | Symlink | Global git ignore patterns. |
| `tmux.conf` | Symlink | tmux configuration. |
| `vim/*` | Symlink | vim plugins and color schemes. |
| `vimrc` | Symlink | vim configuration. |
| `zshenv` | Symlink | Environment for non-interactive shells (mise shims, uv tools). |
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

#### Graphite Worktree Functions

| Function | Description | Usage |
| --- | --- | --- |
| `gt-worktree-create` | Create a git worktree with full project setup, registered with Graphite. | `gt-worktree-create <branch-name>` |
| `gt-worktree-remove` | Remove a worktree after its PR merges and run `gt sync`. | `gt-worktree-remove [<path>] [options]` |

#### Maintenance and Media Functions

| Function | Description | Usage |
| --- | --- | --- |
| `brew-maintain` | Update, upgrade, autoremove, and clean up Homebrew. | `brew-maintain` |
| `ffmpeg-reduce-size` | Re-encode a video to reduce its file size. | `ffmpeg-reduce-size <video-file>` |

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

`make set-up/idb` finishes the idb setup after Homebrew dependencies are
installed. The idb companion is managed by Homebrew, and the Python client is
managed as a `uv` tool so the `idb` executable is available from `~/.local/bin`.

## Services

Long-running launchd services live in `services/`, each with its own install
and uninstall scripts. Services are per-machine opt-ins: the repository
propagates them between computers, but they are not part of `make set-up/all`
and their dependencies are not in the Brewfile. Install a service (and the
dependencies its installer asks for) only on the machine that should run it.

| Service | Description |
| --- | --- |
| `scan-ocr` | Watches `/Users/Shared/Scans` and OCRs incoming PDFs into iCloud Drive. Requires `ocrmypdf` on that machine. Install with `services/scan-ocr/install.sh`. |

## AI Agents

The Claude configuration in `dotfiles/link/claude/` is the source of truth for
all three CLI agents on this machine. Codex CLI (`~/.codex`), Gemini CLI
(`~/.gemini`), and the agentskills.io path (`~/.agents`) receive the same
instructions and skills through symlinks, so `CLAUDE.md` and `skills/` are
maintained once.

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
