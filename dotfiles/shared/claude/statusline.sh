#!/bin/bash
# statusline.sh - Minimal status line showing model and context usage.

# --- Input ---

# A single jq pass extracts the model name and computes context usage, since
# this script runs on every status line refresh.
IFS=$'\t' read -r model context_pct <<< "$(jq -r '
  [
    (.model.display_name // ""),
    (if .context_window.current_usage != null
        and (.context_window.context_window_size // 0) > 0 then
      ((.context_window.current_usage
        | (.input_tokens // 0)
          + (.cache_creation_input_tokens // 0)
          + (.cache_read_input_tokens // 0))
        * 100 / .context_window.context_window_size
        | floor | tostring) + "%"
    else "" end)
  ] | @tsv')"

# --- Colors ---

CORAL=$'\033[38;5;173m'  # Anthropic brand color
DIM=$'\033[2m'
RESET=$'\033[0m'

# --- Output ---

if [ -n "$model" ] && [ -n "$context_pct" ]; then
  printf "${CORAL}%s${RESET} ${DIM}·${RESET} %s" "$model" "$context_pct"
elif [ -n "$model" ]; then
  printf "${CORAL}%s${RESET}" "$model"
fi
