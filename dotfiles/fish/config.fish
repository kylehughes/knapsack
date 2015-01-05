###############
# Instantiation
###############

# Source local profile
. $HOME/.config/fish/profile.fish

############
# Appearance
############

# Color scheme: Base16 Ocean
eval sh $HOME/.config/fish/colors/base16_ocean.dark.sh

# Colorize maven output
alias mvn="$HOME/.config/fish/scripts/maven-antsy-color/mvn"
