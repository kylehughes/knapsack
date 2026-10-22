#!/bin/sh
# reflow-tabs.sh — adaptive multi-row tmux window list.
#
# Stacks the window/tab list across bottom status rows (1..5), packing tabs by
# their measured width and wrapping to the next row when one fills. Only the row
# partition is computed here; names, current-window highlight, and mouse click
# targets stay live tmux format placeholders so they re-expand on every redraw.
#
# Usage: reflow-tabs.sh [session-name]
#   Invoked from tmux hooks in ~/.tmux.conf. Falls back to the current session.

set -eu

MAX_ROWS=5        # tmux hard cap on status lines.
TAB_OVERHEAD=5    # Columns each tab adds around the name: ' #I ' padding + separator.
SAFETY_MARGIN=2   # Keep rows from packing flush to the edge and clipping a tab.

session="${1:-$(tmux display-message -p '#{session_name}')}"

# Moshi/iPhone guard: keep the single-row default layout. The existing if-shell
# block in ~/.tmux.conf already blanks status-left/right for these clients so
# Moshi's window-swipe gesture detection stays reliable.
if tmux show-environment -t "$session" MOSHI_CLIENT 2>/dev/null | grep -q '^MOSHI_CLIENT='; then
  tmux set -gu status-format \; set -g status on
  exit 0
fi

# Reflow to the widest client attached to this session. aggressive-resize sizes
# the window to that client, so its width is the right basis for capacity.
width=$(tmux list-clients -t "$session" -F '#{client_width}' 2>/dev/null | sort -n | tail -1)

# Detached session (e.g. created without a client): defer to the client-attached hook.
[ -n "$width" ] || { tmux set -g status on; exit 0; }

# Row 0 carries the status-left (#S) block; continuation rows are indented by an
# equal-width pad so every row's tabs line up under it. Measure that block's
# rendered display width (expand it, strip the #[...] style markup, count the
# remaining glyphs) so it tracks the session name and theme automatically.
LEFT0='#{T;=/#{status-left-length}:status-left}'
left_width=$(tmux display-message -p -t "$session" "$LEFT0" 2>/dev/null | awk '{ gsub(/#\[[^]]*\]/, ""); print length }')
[ -n "$left_width" ] || left_width=0
pad=$(printf '%*s' "$left_width" '')

# Usable width for tabs is the same on every row (row 0 spends it on status-left,
# later rows on the matching pad).
content_width=$(( width - left_width - SAFETY_MARGIN ))
[ "$content_width" -ge 10 ] || content_width=$width

# Pack tabs into rows by measured width: fill a row until the next tab won't fit,
# then wrap to the next row. Windows stay in index order, so each row is a
# contiguous index range [lo,hi] that the #{W:...} gate below can select.
# `bounds` collects each row's last window index; the final row uses a 9999
# sentinel so any tail beyond MAX_ROWS overflows into it (tmux trims it, keeping
# the active window in focus). Measure the displayed name (#{E:@window_name},
# which honors any truncation) so packing matches what's actually rendered, not
# the raw name. Names may contain spaces, so split each line on the first only.
bounds=""
row=0
used=0
prev_idx=0
oldIFS=$IFS
IFS='
'
for line in $(tmux list-windows -t "$session" -F '#{window_index} #{E:@window_name}' 2>/dev/null); do
  idx=${line%% *}
  name=${line#* }
  tabw=$(( ${#idx} + ${#name} + TAB_OVERHEAD ))
  if [ "$used" -gt 0 ] && [ $(( used + tabw )) -gt "$content_width" ] && [ "$row" -lt $(( MAX_ROWS - 1 )) ]; then
    bounds="$bounds $prev_idx"
    row=$(( row + 1 ))
    used=0
  fi
  used=$(( used + tabw ))
  prev_idx=$idx
done
IFS=$oldIFS
bounds="$bounds 9999"
rows=$(( row + 1 ))

# tmux's status option takes off/on/2..5; a single line is "on", not "1".
if [ "$rows" -le 1 ]; then status_val=on; else status_val=$rows; fi

# status-format[i] replaces the whole construction of status line i, so each row
# template rebuilds the line: only row 0 carries the status-left (#S) block, and
# each row's #{W:...} loop is gated to render only the windows whose index falls
# in that row's [lo,hi] range. renumber-windows + base-index 1 keep indices
# contiguous (1..N), so the index range == the row's slice.
#
# Accumulate one atomic tmux command in the positional params ($@). A bare ";"
# argument is tmux's own command separator, so this issues every set in a single
# invocation with no eval and no quoting hazards. set -gu clears the array first
# so shrinking the row count (e.g. 5 -> 2) leaves no stale status-format[2..4].
set -- set -gu status-format ";" set -g status "$status_val"

# The two per-window sub-templates are constant across rows (they mirror tmux's
# own non-current / current window arms), so define them once. #{W:a,b} applies
# arg a to non-current windows and b to the current one; only the per-row index
# gate below varies, and each arm is gated to blank windows outside its row.
other='#[range=window|#{window_index} #{E:window-status-style}]#[push-default]#{T:window-status-format}#[pop-default]#[norange default]#{?loop_last_flag,,#{E:window-status-separator}}'
curr='#[range=window|#{window_index} list=focus #{E:window-status-current-style}]#[push-default]#{T:window-status-current-format}#[pop-default]#[norange list=on default]#{?loop_last_flag,,#{E:window-status-separator}}'

lo=1
i=0
for hi in $bounds; do
  if [ "$i" -eq 0 ]; then left="$LEFT0"; else left="$pad"; fi

  gate='#{&&:#{e|>=:#{window_index},'"$lo"'},#{e|<=:#{window_index},'"$hi"'}}'
  loop='#{W:#{?'"$gate"','"$other"',},#{?'"$gate"','"$curr"',}}'

  fmt="#[align=left range=left #{E:status-left-style}]#[push-default]${left}#[pop-default]#[norange default]#[list=on align=left]#[list=left-marker]<#[list=right-marker]>#[list=on]${loop}#[nolist align=right range=right #{E:status-right-style}]#[push-default]#{T;=/#{status-right-length}:status-right}#[pop-default]#[norange default]"

  set -- "$@" ";" set -g "status-format[$i]" "$fmt"
  lo=$(( hi + 1 ))
  i=$(( i + 1 ))
done

tmux "$@"
