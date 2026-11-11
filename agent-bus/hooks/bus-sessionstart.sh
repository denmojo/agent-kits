#!/usr/bin/env bash
# SessionStart hook for a live bus session: print the agent-bus catch-up block
# into context (with the reply command for each unread sender and thread), then
# tell the session to arm its bus watcher.
#
# Which agent this session is: $BUS_AGENT when set, else the tmux session name.
# The hook stays silent unless the registry marks that agent with wake "live".
# Headless agents set AGENT_NAME and are skipped.
#
# Local additions go in <root>/bus-hooks.local, sourced before anything else.
# It may exit early, and may define bus_extra_lines <agent> to print more lines
# after the arm line.
# Never fails the session: errors are swallowed, exit 0.

[ -n "${AGENT_NAME:-}" ] && exit 0
ROOT="${AGENTS_ROOT:-$HOME/agents}"
BIN="${BUS_BIN:-$HOME/bin}"
[ -f "$ROOT/bus-hooks.local" ] && . "$ROOT/bus-hooks.local"
AGENT="${BUS_AGENT:-}"
if [ -z "$AGENT" ]; then
  [ -n "${TMUX:-}" ] || exit 0
  AGENT="$(tmux display-message -p '#S' 2>/dev/null)"
fi
[ -n "$AGENT" ] || exit 0
python3 -I - "$BIN" "$AGENT" 2>/dev/null <<'PY' || exit 0
import sys
sys.path.insert(0, sys.argv[1])
import agentbus
sys.exit(0 if agentbus.live_session(sys.argv[2]) else 1)
PY

ARM="Arm the bus watcher: run 'agent-inbox $AGENT --wait' as a background Bash command."

peek=$("$BIN/agent-inbox" "$AGENT" --peek 2>/dev/null)
standin=$(python3 -I - "$BIN" "$AGENT" 2>/dev/null <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import agentbus
fallback = agentbus.registry().get(sys.argv[2], {}).get("fallback")
if fallback:
    cur = agentbus._load_cursor(sys.argv[2])
    for t in agentbus.threads():
        last = cur.get(t, -1)
        for m in agentbus.read_thread_safe(t):
            if m.sender == fallback and m.index > last:
                print("[%s] %s -> %s (%s): %s" % (m.thread, m.sender, m.to, m.ts, m.body))
PY
)
replies=""
[ -n "$peek" ] && replies=$(python3 -I - "$BIN" "$AGENT" 2>/dev/null <<'PY'
import sys
sys.path.insert(0, sys.argv[1])
import agentbus
notes, replies = agentbus.delivery_notes(sys.argv[2], agentbus.unread(sys.argv[2], []))
print("\n".join(replies))
PY
)

if [ -n "$peek" ] || [ -n "$standin" ]; then
  echo "Agent bus catch-up:"
  [ -n "$peek" ] && echo "$peek"
  [ -n "$replies" ] && echo "$replies"
  if [ -n "$standin" ]; then
    echo "On-call replies since your cursor:"
    echo "$standin"
  fi
fi
echo "$ARM"
type bus_extra_lines >/dev/null 2>&1 && bus_extra_lines "$AGENT"
exit 0
