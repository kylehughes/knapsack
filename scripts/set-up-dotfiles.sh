#!/usr/bin/env bash
#===============================================================================
#  set-up-dotfiles — Install dotfiles by creating symlinks and copies
#
#  USAGE:
#    ./scripts/set-up-dotfiles.sh
#
#  OPTIONS:
#    None
#
#  REQUIREMENTS:
#    bash ≥ 3.x, coreutils (cp, ln, cmp)
#
#  EXIT CODES:
#    0  success
#    1  usage error (bad flags, etc.)
#    2  missing dependency
#    >2 script-specific failures
#
#  AUTHOR:      Kyle Hughes <kyle@kylehugh.es>
#  LICENSE:     MIT
#===============================================================================

set -euo pipefail

# --- Constants ---

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PATH_DOTFILES="$REPO_ROOT/dotfiles"

# --- Logging Functions ---

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

# --- Copy Action Functions ---

function action_copy_header() {
    log_header "copying files into home directory: $HOME"
}

# Test if file should be copied.
# Returns: skip reason if file should be skipped, empty otherwise.
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

# --- Link Action Functions ---

function action_link_header() {
    log_header "linking files into home directory: $HOME"
}

# Test if file should be linked.
# Returns: skip reason if file should be skipped, empty otherwise.
function action_link_test() {
    [[ "$1" -ef "$2" ]] && echo "same file" || true
}

function action_link_do() {
    log_success "linking $HOME/$1"
    ln -sf "$2" "$HOME/$1"
}

# Process files for the specified action (copy or link).
# Args: $1 - action type
function do_action() {
    local fileBase fileDest skip
    local action="$1"
    local action_dir="$PATH_DOTFILES/$action"

    if [[ ! -d "$action_dir" ]]; then
        log_arrow "no $action directory found, skipping"
        return
    fi

    local dotfiles=("$action_dir"/*)
    
    if [[ ! -e "${dotfiles[0]}" ]]; then
        log_arrow "no files to $action"
        return
    fi

    # Run header function if it exists.
    [[ $(declare -f "action_${action}_header") ]] && "action_${action}_header"

    for file in "${dotfiles[@]}"; do
        fileBase=".$(basename "$file")"
        fileDest="$HOME/$fileBase"

        # Handle directories.
        if [[ -d "$file" ]]; then
            # Special handling for .config to maintain XDG structure.
            if [[ "$fileBase" == ".config" ]]; then
                mkdir -p "$HOME/.config"
                
                for configdir in "$file"/*; do
                    if [[ -d "$configdir" ]]; then
                        configBase="$(basename "$configdir")"
                        configDest="$HOME/.config/$configBase"
                        log_success "linking $configDest"
                        ln -sfn "$configdir" "$configDest"
                    fi
                done
                continue
            fi
            
            # For other directories, link files and subdirectories.
            mkdir -p "$fileDest"

            for subfile in "$file"/*; do
                subfileBase="$(basename "$subfile")"
                if [[ -f "$subfile" ]]; then
                    log_success "linking $fileDest/$subfileBase"
                    ln -sf "$subfile" "$fileDest/$subfileBase"
                elif [[ -d "$subfile" ]]; then
                    log_success "linking $fileDest/$subfileBase"
                    ln -sfn "$subfile" "$fileDest/$subfileBase"
                fi
            done
            continue
        fi

        # Test if file should be processed.
        if [[ $(declare -f "action_${action}_test") ]]; then
            skip="$(action_${action}_test "$file" "$fileDest")"
            if [[ "$skip" ]]; then
                log_error "skipping $HOME/$fileBase: $skip"
                continue
            fi
        fi

        # Process the file.
        "action_${action}_do" "$fileBase" "$file"
    done
}

# --- Main ---

do_action "copy"
do_action "link"
log_header "done"