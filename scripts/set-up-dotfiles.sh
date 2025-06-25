#!/bin/bash

#
# set-up-dotfiles.sh
# Sets up dotfiles by creating symlinks and copying files
#

set -euo pipefail

##############################
# CONSTANTS
##############################

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATH_DOTFILES="$REPO_ROOT/dotfiles"

##############################
# UTILITY FUNCTIONS
##############################

# Logging
function log_header()   {
    echo -e "\n\033[1m$@\033[0m";
}
function log_success() {
    echo -e " \033[1;32m\033[0m  $@";
}
function log_error() {
    echo -e " \033[1;31m\033[0m  $@";
}
function log_arrow() {
    echo -e " \033[1;34m�\033[0m  $@";
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
    ln -sf "$2" "$HOME/$1"
}

function do_action() {
    local fileBase fileDest skip
    local action="$1"
    local action_dir="$PATH_DOTFILES/$action"

    # check if action directory exists
    if [[ ! -d "$action_dir" ]]; then
        log_arrow "no $action directory found, skipping"
        return
    fi

    local dotfiles=("$action_dir"/*)
    
    # abort if no files
    if [[ ! -e "${dotfiles[0]}" ]]; then
        log_arrow "no files to $action"
        return
    fi

    # run action's _header function if declared
    [[ $(declare -f "action_${action}_header") ]] && "action_${action}_header"

    # iterate over dotfiles
    for file in "${dotfiles[@]}"; do
        fileBase=".$(basename "$file")"
        fileDest="$HOME/$fileBase"

        # handle directories with files inside (preserve structure)
        if [[ -d "$file" ]]; then
            # special handling for .config directory
            if [[ "$fileBase" == ".config" ]]; then
                # ensure .config exists
                mkdir -p "$HOME/.config"
                
                # process subdirectories in .config
                for configdir in "$file"/*; do
                    if [[ -d "$configdir" ]]; then
                        configBase="$(basename "$configdir")"
                        configDest="$HOME/.config/$configBase"
                        
                        # create symlink for entire config subdirectory
                        log_success "linking $configDest"
                        ln -sfn "$configdir" "$configDest"
                    fi
                done
                continue
            fi
            
            # for other directories, ensure target exists
            mkdir -p "$fileDest"
            
            # process files within the directory
            for subfile in "$file"/*; do
                if [[ -f "$subfile" ]]; then
                    subfileBase="$(basename "$subfile")"
                    log_success "linking $fileDest/$subfileBase"
                    ln -sf "$subfile" "$fileDest/$subfileBase"
                fi
            done
            continue
        fi

        # run action's _test function if declared
        if [[ $(declare -f "action_${action}_test") ]]; then
            skip="$(action_${action}_test "$file" "$fileDest")"
            if [[ "$skip" ]]; then
                log_error "skipping $HOME/$fileBase: $skip"
                continue
            fi
        fi

        # run action
        "action_${action}_do" "$fileBase" "$file"
    done
}

##############################
# MAIN SCRIPT
##############################

# do setup actions
do_action "copy"
do_action "link"

# finish
log_header "done"