# Knapsack by/for Kyle Hughes

## Installation

1. Clone the repository to your home (`~/`) directory.
1. If on OS X, install the Homebrew package manager:

    ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/install)"

1. Install all the tools manually without direction (sorry!).
1. Set `$KNAPSACK` environment variable to root knapsack location for local shell.
1. Pull down the submodules:

    git submodule update --init --recursive
				
1. Setup symlinks.

## Contents

### Dotfiles (../dotfiles/) 

#### fish (../fish/)

**Install:**
	
	brew install fish

#### git (../git/)

`gitconfig`: The global configuration file. All settings should be applicable to all git environments. This picks up the local configuration profile through an `include`.

`gitconfig_local_template`: A minimal template for the local configuration file.

`gitconfig_local`: The local configuration file (not included, ignored through the local `.gitignore`).

#### tmux

    brew install tmux

- [tmuxifier][dotfiles_tmuxifier]: layout management and niceties

[dotfiles_tmuxifier]: https://github.com/jimeh/tmuxifier

### Resources

#### Wallpapers

The naming scheme for wallpapers is: `{title}_{width}x{height}`.

