# Knapsack by/for Kyle Hughes

## Installation

1. Clone the repository to your home (`~/`) directory.
2. Install all the tools manually without direction (sorry!).
3. Pull down the submodules:

    git submodule update --init --recursive
				
4. Setup symlinks.

## Contents

### Dotfiles (.../dotfiles/) 

#### git (.../git/)

`gitconfig`: The global configuration file. All settings should be applicable to all git environments. This picks up the local
configuration profile through an `include`.

`gitconfig_local_template`: A minimal template for the local configuration file.

`gitconfig_local`: **This file is not included in the repository, and is ignored through the local `.gitignore`**

#### tmux

**Install:**

    brew install tmux

- [tmuxifier][dotfiles_tmuxifier]: layout management and niceties

[dotfiles_tmuxifier]: https://github.com/jimeh/tmuxifier

### Resources

#### Wallpapers

The naming scheme for wallpapers is: `{title}_{width}x{height}`.

