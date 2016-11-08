# Knapsack by/for Kyle Hughes

## Installation

1. Clone the repository to your home (`~/`) directory.
1. If on OS X, install the Homebrew package manager:

    ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

1. Pull down the submodules:

    git submodule update --init --recursive

1. Run the setup script to create symlinks to / copy config files:

    cd dotfiles
	./setup.sh

### Additional Setup

- Install the [Homebrew package manager][installation_homebrew] *(*OS X only)*

[installation_homebrew]: http://brew.sh

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

### Credits

- Ben Alman's [dotfile bootstrapping pattern][credits_ben-alman]

[credits_ben-alman]: https://github.com/cowboy/dotfiles
