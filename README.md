# Knapsack by/for Kyle Hughes

## Installation

1. Clone the repository to your home (`~/`) directory.
1. If on OS X, install the Homebrew package manager:

		ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

1. Install all the tools manually without direction (sorry).
1. Set `$KNAPSACK` environment variable to root knapsack location for preferred shell.
1. Pull down the submodules:

    	git submodule update --init --recursive

1. Run `dotfiles/setup.sh` to setup symlinks.

## Contents

### Dotfiles (../dotfiles/)

#### git (../dotfiles/git/)

`gitconfig`: The global configuration file. All settings should be applicable to all git environments. This picks up the local configuration profile through an `include`.

`gitconfig_local_template`: A minimal template for the local configuration file.

`gitconfig_local`: The local configuration file (not included, ignored through the local `.gitignore`).

#### tmux (../dotfiles/tmux/)

    brew install tmux

- [tmux copy & OS X][dotfiles_tmux-copy]: setting up tmux copy-mode to use the OS X system clipboard
- [tmuxinator][dotfiles_tmuxinator]: layout management

[dotfiles_tmux-copy]: https://robots.thoughtbot.com/tmux-copy-paste-on-os-x-a-better-future
[dotfiles_tmuxinator]: https://github.com/tmuxinator/tmuxinator

### Resources

#### Wallpapers

The naming scheme for wallpapers is: `{title}_{width}x{height}`.

### Credits

- Ben Alman's [https://github.com/cowboy/dotfiles dotfile bootstrapping pattern]
