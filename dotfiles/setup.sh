#!/bin/bash

if [[ "$1" == "-h" || "$1" == "--help" ]]; then cat <<HELP
Usage: $(basename "$0")

See the README for documentation:
https://github.com/kylehughes/knapsack

Copyright (c) 2016 Kyle Hughes
Licensed under the MIT License:
https://opensource.org/licenses/MIT
HELP
exit; fi

##############################
# CONSTANTS
##############################

PATH_DOTFILES=$(pwd)

##############################
# UTILITY FUNCTIONS
##############################

# Logging
function log_header()   {
    echo -e "\n\033[1m$@\033[0m";
}
function log_success() {
    echo -e " \033[1;32m✔\033[0m  $@";
}
function log_error() {
    echo -e " \033[1;31m✖\033[0m  $@";
}
function log_arrow() {
    echo -e " \033[1;34m➜\033[0m  $@";
}

##############################
# ACTION PROCESSING
##############################

# copy files
function action_copy_header() {
    log_header "copying files into home directory: $HOME"
}
function action_copy_test() {
    if [[ -e "$2" && ! "$(cmp "$1" "$2" 2> /dev/null)" ]]; then
        echo "same file"
    elif [[ "$1" -ot "$2" ]]; then
        echo "destination file newer"
    fi
}
function action_copy_do() {
    log_success "copying $HOME/$1"
    cp "$2" "$HOME/$1"
}

# link files
function action_link_header() {
    log_header "linking files into home directory: $HOME"
}
function action_link_test() {
    [[ "$1" -ef "$2" ]] && echo "same file"
}
function action_link_do() {
    log_success "linking $HOME/$1"
    ln -sf $2 $HOME/$1
}

function do_action() {
    local fileBase fileDest skip

    local dotfiles=($PATH_DOTFILES/$1/*)
    [[ $(declare -f "action_$1_files") ]] && dotfiles=($(action_$1_files "${dotfiles[@]}"))

    # abort if no files
    if (( ${#dotfiles[@]} == 0 )); then
        log_error "no files to act on for action: $1"
        return;
    fi

    # run action's _header function if declared
    [[ $(declare -f "action_$1_header") ]] && "action_$1_header"

    # iterate over dotfiles
    for file in "${dotfiles[@]}"; do
        fileBase=".$(basename $file)"
        fileDest="$HOME/$fileBase"

        # run action's _test function if declared
        if [[ $(declare -f "action_$1_test") ]] && "action_$1_test"; then
            # skip file if test returns something
            skip="$("action_$1_test" "$file" "$fileDest")"
            if [[ "$skip" ]]; then
                log_error "skipping $HOME/$fileBase: $skip"
                continue
            fi
        fi

        # run action
        "action_$1_do" "$fileBase" "$file"
    done
}

##############################
# MAIN SCRIPT
##############################

cd $PATH_DOTFILES

# do setup actions
do_action "copy"
do_action "link"

# finish
log_header "! done !"
