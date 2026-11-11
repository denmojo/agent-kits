"""Tests for the live-session bus hooks, run as subprocesses on a temp root with a fake tmux."""
import json
import os
import subprocess
from pathlib import Path

BIN = Path(__file__).resolve().parent.parent
HOOKS = BIN / "hooks"


def fake_tmux(tmp_path, name):
    d = tmp_path / ("fakebin-" + name)
    d.mkdir(exist_ok=True)
    t = d / "tmux"
    t.write_text("#!/bin/sh\necho %s\n" % name)
    t.chmod(0o755)
    return d


def run(hook, tmp_path, session="claude", env=None):
    e = {k: v for k, v in os.environ.items()
         if k not in ("AGENT_NAME", "BUS_AGENT", "AGENTBUS_NOW")}
    e["AGENTS_ROOT"] = str(tmp_path)
    e["TMUX"] = "/tmp/fake,1,0"
    e["BUS_BIN"] = str(BIN)
    e["PATH"] = str(fake_tmux(tmp_path, session)) + os.pathsep + e["PATH"]
    e.update(env or {})
    r = subprocess.run([str(HOOKS / hook)], env=e, capture_output=True, text=True, timeout=10)
    assert r.returncode == 0
    run.stderr = r.stderr
    return r.stdout


def setup_root(tmp_path):
    (tmp_path / "claude").mkdir(exist_ok=True)
    reg = {n: {"wake": "none", "model": "", "home": "", "rate_cap_per_hour": 6, "timeout_s": 0}
           for n in ("claude", "claude2", "claude-oncall", "pat", "tester")}
    reg["claude"].update(wake="live", fallback="claude-oncall")
    reg["claude2"]["wake"] = "live"
    reg["pat"]["human"] = True
    (tmp_path / "registry.json").write_text(json.dumps(reg))


def say(tmp_path, who, to, thread, body):
    e = {k: v for k, v in os.environ.items() if k not in ("AGENT_NAME", "BUS_AGENT")}
    e.update(AGENTS_ROOT=str(tmp_path), AGENT_NAME=who)
    subprocess.run([str(BIN / "agent-say"), "--to", to, "--thread", thread, body],
                   env=e, check=True, capture_output=True, text=True)


ARM = "Arm the bus watcher: run 'agent-inbox %s --wait' as a background Bash command."
DEAD = "Bus watcher is not armed: run 'agent-inbox %s --wait' as a background Bash command."


def test_context_dead_watcher_missing(tmp_path):
    setup_root(tmp_path)
    assert run("bus-context.sh", tmp_path).strip() == DEAD % "claude"
    assert run.stderr == ""


def test_context_unparseable_and_dead_pid(tmp_path):
    setup_root(tmp_path)
    pidf = tmp_path / "claude" / "watcher.pid"
    pidf.write_text("junk\n")
    assert run("bus-context.sh", tmp_path).strip() == DEAD % "claude"
    pidf.write_text("999999\n")
    assert run("bus-context.sh", tmp_path).strip() == DEAD % "claude"


def test_context_live_watcher_silent(tmp_path):
    setup_root(tmp_path)
    (tmp_path / "claude" / "watcher.pid").write_text("%d\n" % os.getpid())
    assert run("bus-context.sh", tmp_path) == ""


def test_session_not_marked_live_is_silent(tmp_path):
    setup_root(tmp_path)
    for session in ("other", "tester", "claude-oncall"):
        assert run("bus-context.sh", tmp_path, session=session) == ""
        assert run("bus-sessionstart.sh", tmp_path, session=session) == ""


def test_headless_agent_is_silent(tmp_path):
    setup_root(tmp_path)
    assert run("bus-context.sh", tmp_path, env={"AGENT_NAME": "x"}) == ""
    assert run("bus-sessionstart.sh", tmp_path, env={"AGENT_NAME": "x"}) == ""


def test_missing_registry_is_silent(tmp_path):
    assert run("bus-context.sh", tmp_path) == ""
    assert run("bus-sessionstart.sh", tmp_path) == ""


def test_bus_agent_names_the_session_without_tmux(tmp_path):
    setup_root(tmp_path)
    out = run("bus-sessionstart.sh", tmp_path, session="other", env={"BUS_AGENT": "claude2", "TMUX": ""})
    assert out.strip() == ARM % "claude2"
    assert run("bus-sessionstart.sh", tmp_path, session="claude", env={"TMUX": ""}) == ""


def test_sessionstart_only_arm_line_when_empty(tmp_path):
    setup_root(tmp_path)
    assert run("bus-sessionstart.sh", tmp_path).strip() == ARM % "claude"


def test_sessionstart_lists_unread_and_standin_replies(tmp_path):
    setup_root(tmp_path)
    say(tmp_path, "tester", "claude", "t1", "ping from tester")
    say(tmp_path, "claude-oncall", "pat", "t2", "oncall says hello")
    out = run("bus-sessionstart.sh", tmp_path)
    lines = out.strip().split("\n")
    assert lines[0] == "Agent bus catch-up:"
    assert "ping from tester" in out
    assert "oncall says hello" in out
    assert lines[-1] == ARM % "claude"
    # claude2 names no fallback, so the stand-in's reply is not listed for it
    assert "oncall says hello" not in run("bus-sessionstart.sh", tmp_path, session="claude2")


def test_sessionstart_prints_reply_form(tmp_path):
    setup_root(tmp_path)
    say(tmp_path, "tester", "claude", "t1", "ping")
    lines = run("bus-sessionstart.sh", tmp_path).strip().split("\n")
    assert ('Reply: AGENT_NAME=claude agent-say --to tester --thread t1 --status answered "<text>"'
            in lines)
    assert not [l for l in lines if l.startswith("Re-arm:")]  # the arm line covers it
    empty = tmp_path / "empty"
    empty.mkdir()
    setup_root(empty)
    assert "Reply:" not in run("bus-sessionstart.sh", empty)


def test_second_session_gets_its_own_lines(tmp_path):
    setup_root(tmp_path)
    assert run("bus-sessionstart.sh", tmp_path, session="claude2").strip() == ARM % "claude2"
    assert run("bus-context.sh", tmp_path, session="claude2").strip() == DEAD % "claude2"
    (tmp_path / "claude2").mkdir()
    (tmp_path / "claude2" / "watcher.pid").write_text("%d\n" % os.getpid())
    assert run("bus-context.sh", tmp_path, session="claude2") == ""
    assert run("bus-context.sh", tmp_path) != ""  # claude's own watcher is still down


def test_local_file_can_add_lines_and_exit_early(tmp_path):
    setup_root(tmp_path)
    (tmp_path / "bus-hooks.local").write_text(
        '[ "${SKIP_BUS:-}" = "1" ] && exit 0\n'
        'bus_extra_lines() { [ "$1" = "claude" ] && echo "extra line for claude"; return 0; }\n')
    assert run("bus-sessionstart.sh", tmp_path).strip().split("\n") == [ARM % "claude", "extra line for claude"]
    assert run("bus-sessionstart.sh", tmp_path, session="claude2").strip() == ARM % "claude2"
    assert run("bus-sessionstart.sh", tmp_path, env={"SKIP_BUS": "1"}) == ""
    assert run("bus-context.sh", tmp_path, env={"SKIP_BUS": "1"}) == ""
