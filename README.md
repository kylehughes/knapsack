# knapsack

Personal dotfiles and development environment configuration for macOS.

## Installation

```sh
# Clone repository
cd ~ && git clone git@github.com:kylehughes/knapsack.git

# Install Homebrew
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install dependencies
cd ~/knapsack && brew bundle install

# Update submodules
git submodule update --init --recursive

# Install dotfiles
cd dotfiles && ./setup.sh
```

## Structure

### Dotfiles

Configuration files managed by `dotfiles/setup.sh`:

| Configuration | Type | Description |
| --- | --- | --- |
| `claude/CLAUDE.md` | Symlink | Claude AI configuration |
| `config/ghostty/*` | Symlink | Ghostty terminal configuration |
| `gitconfig` | Symlink | Global git configuration |
| `gitconfig_local` | Copy | Local git overrides (not tracked) |
| `tmux.conf` | Symlink | tmux configuration |
| `vim/*` | Symlink | vim configuration and plugins |
| `vimrc` | Symlink | vim configuration |
| `zshrc` | Symlink | zsh shell configuration |

### Gengar Theme

A consistent purple theme across all terminal applications:

| Color | Hex | Usage |
| --- | --- | --- |
| Background | `#1c1c1c` | Terminal background |
| Foreground | `#eeeeee` | Primary text |
| Purple | `#af5fff` | Status bars, borders |
| Bright Purple | `#d7afff` | Active elements |
| Grey | `#444444` | Inactive elements |

### Dependencies

Managed via `Brewfile`:

```sh
brew bundle install    # Install all dependencies
brew bundle check      # Check for missing packages
brew bundle cleanup    # Remove unlisted packages
```