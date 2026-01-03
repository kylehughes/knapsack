#!/bin/bash
# statusline.sh - Minimal status line showing model and context usage.
input=$(cat)

# --- Model ---
model=$(echo "$input" | jq -r '.model.display_name // empty')

# --- Context Usage ---
usage=$(echo "$input" | jq '.context_window.current_usage')
context_limit=$(echo "$input" | jq -r '.context_window.context_window_size // 0')

context_pct=""
if [ "$usage" != "null" ] && [ "$context_limit" -gt 0 ] 2>/dev/null; then
  current_tokens=$(echo "$usage" | jq '.input_tokens + .cache_creation_input_tokens + .cache_read_input_tokens')
  pct=$((current_tokens * 100 / context_limit))
  context_pct="${pct}%"
fi

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
