#!/usr/bin/env bash
# UserPromptSubmit hook for a live bus session: one line when the agent-bus
# watcher is dead (pid file missing, unparseable, or pid gone).
#
# Which agent this session is: $BUS_AGENT when set, else the tmux session name.
# Silent unless the registry marks that agent with wake "live". Headless agents
# set AGENT_NAME and are skipped. <root>/bus-hooks.local is sourced first and
# may exit early.
# Exit 0 always.

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

pid=""
[ -f "$ROOT/$AGENT/watcher.pid" ] && pid=$(tr -d '[:space:]' < "$ROOT/$AGENT/watcher.pid" 2>/dev/null)
case "$pid" in
  ''|*[!0-9]*) alive=0 ;;
  *) kill -0 "$pid" 2>/dev/null && alive=1 || alive=0 ;;
esac
[ "$alive" = 1 ] || echo "Bus watcher is not armed: run 'agent-inbox $AGENT --wait' as a background Bash command."
exit 0
