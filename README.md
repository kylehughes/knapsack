# knapsack

`COMPUTER THINGS FOR KYLE`

## Installation (macOS)

Run the following commands in a shell - `zsh` is expected. Eventually, turn this all into a script.

###### Set `zsh` as the default login shell:

```
chsh -s /bin/zsh
```

*Note:* Make sure your terminal emulator is configured to use the login shell. Otherwise you'll have to set its shell manually.

###### Clone the repository to your home directory:

```sh
cd ~ && git clone git@github.com:kylehughes/knapsack.git
```

###### Install the Homebrew package manager:

```sh
ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"
```

###### Install Homebrew packages:

Install all dependencies using the Brewfile:

```sh
brew bundle install
```

This will install all formulae, casks, and VS Code extensions defined in the `Brewfile`.

###### Update the submodule repositories:

```sh
git submodule update --init --recursive
```

###### Run the dotfiles setup script:

Configures the file system for the included "dotfiles." Hard copy or symlink depending on the file.

```sh
cd dotfiles && ./setup.sh
```

## Contents

### Applications (`./applications/`)

### Dotfiles (`./dotfiles/`)

#### Claude Configuration

| File              | Link Type | Purpose                                                                                                                                            |
| ----------------- | --------- | -------------------------------------------------------------------------------------------------------------------------------------------------- |
| `claude/CLAUDE.md`| Symlink   | Global configuration for Claude AI. Installed to `~/.claude/CLAUDE.md`.                                                                           |

#### `git` Dotfiles

| File              | Link Type | Purpose                                                                                                                                                                            |
| ----------------- | --------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `gitconfig`       | Symlink   | The global configuration file. All settings should be applicable to all `git` environments. This picks up the local configuration profile through an `include`.                    |
| `gitconfig_local` | Copy      | The local `git` configuration file, providing an avenue to override default **knapsack** settings. *Note*: Not included in source control, ignored through the local `.gitignore`. |

#### `tmux` Dotfiles

- [tmux copy & OS X][dotfiles_tmux-copy]: setting up tmux copy-mode to use the OS X system clipboard
- [tmuxinator][dotfiles_tmuxinator]: layout management

[dotfiles_tmux-copy]: https://robots.thoughtbot.com/tmux-copy-paste-on-os-x-a-better-future
[dotfiles_tmuxinator]: https://github.com/tmuxinator/tmuxinator

#### `vim` Dotfiles

#### `zsh` Dotfiles

### External

### Scripts (`./scripts/`)

## Managing Dependencies with Brewfile

The `Brewfile` in the repository root defines all Homebrew dependencies for this setup. It includes:

- **Formulae**: Command-line tools and libraries
- **Casks**: GUI applications

### Common Brewfile Commands

```sh
# Install all dependencies
brew bundle install

# Update Brewfile from current installation
brew bundle dump --describe

# Check for missing dependencies
brew bundle check

# Clean up dependencies not in Brewfile
brew bundle cleanup
```
