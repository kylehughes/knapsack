###############
# oh-my-fish
###############

# Source local profile
. $HOME/.config/fish/profile.fish

# Path to oh-my-fish
set fish_path $KNAPSACK/external/oh-my-fish

# Path to custom folder
set fish_custom $KNAPSACK/dotfiles/fish/custom

# Built-in Plugins (.../oh-my-fish/plugins/)
set fish_plugins theme

# Load oh-my-fish configuration
. $fish_path/oh-my-fish.fish

###############
# Appearance
###############

# Welcome message
set -g -x fish_greeting ''

# Color scheme: Base16 Ocean
# eval sh $HOME/.config/fish/colors/base16-ocean.dark.sh

# Theme
set fish_theme ocean
