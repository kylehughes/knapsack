##############
# Environment Variables
##############

set -U KNAPSACK $HOME/knapsack
set -U KNAPSACK_FISH $KNAPSACK/dotfiles/fish

set -U default_user kylehugh

###############
# Local Profile
###############

. $KNAPSACK_FISH/profile.fish

###############
# oh-my-fish
###############

# Path to oh-my-fish
set fish_path $KNAPSACK/external/oh-my-fish

# Path to custom folder
set fish_custom $KNAPSACK/dotfiles/fish/custom

# Built-in Plugins (.../oh-my-fish/plugins/)
set fish_plugins git-flow theme

###############
# Appearance
###############

# Welcome message
set -g -x fish_greeting ''

# Theme
set fish_theme agnoster

###############
# Finally...
###############

# Load oh-my-fish configuration
. $fish_path/oh-my-fish.fish
