"""Tests for the agent-bus command-line tools, run as subprocesses on a temp root."""
import json
import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

BIN = Path(__file__).resolve().parent.parent


def _reg(names):
    """A registry for the tests: claude is the live session, pat the person."""
    reg = {n: {"wake": "none", "model": "", "home": "", "rate_cap_per_hour": 6, "timeout_s": 0}
           for n in names}
    if "claude" in reg:
        reg["claude"]["wake"] = "live"
    if "pat" in reg:
        reg["pat"]["human"] = True
    return reg


@pytest.fixture(autouse=True)
def _default_registry(tmp_path):
    """Every test root starts with a registry, since a live session is whatever
    the registry marks live. A test that wants none uses its own directory."""
    (tmp_path / "registry.json").write_text(json.dumps(
        _reg(("claude", "claude-oncall", "pat", "grok", "gemini"))))


def run(tool, *args, root, env=None, stdin=None, timeout=10):
    e = {k: v for k, v in os.environ.items() if k not in ("AGENT_NAME", "AGENTBUS_NOW")}
    e["AGENTS_ROOT"] = str(root)
    e.update(env or {})
    if not (Path(root) / "registry.json").exists() and not (env or {}).get("NO_REGISTRY"):
        (Path(root) / "registry.json").write_text(json.dumps(
            _reg(("claude", "claude-oncall", "pat", "grok", "gemini"))))
    e.pop("NO_REGISTRY", None)
    return subprocess.run([str(BIN / tool), *args], env=e, input=stdin,
                          capture_output=True, text=True, timeout=timeout)


def test_say_requires_agent_name(tmp_path):
    r = run("agent-say", "--to", "claude", "--thread", "t1", "hi", root=tmp_path)
    assert r.returncode == 2
    assert "AGENT_NAME" in r.stderr


def test_say_refuses_the_persons_name(tmp_path):
    r = run("agent-say", "--to", "claude", "--thread", "t1", "hi",
            root=tmp_path, env={"AGENT_NAME": "pat"})
    assert r.returncode == 2


def test_say_posts_and_reads_stdin(tmp_path):
    r = run("agent-say", "--to", "claude", "--thread", "t1", "hello", "there",
            root=tmp_path, env={"AGENT_NAME": "grok", "AGENTBUS_NOW": "2026-10-29 10:00"})
    assert r.returncode == 0
    text = (tmp_path / "bus/threads/t1.md").read_text()
    assert "### 2026-10-29 10:00 · grok → claude · thread t1 · open\nhello there\n" in text
    r = run("agent-say", "--to", "claude", "--thread", "t1", root=tmp_path,
            env={"AGENT_NAME": "grok"}, stdin="line1\nline2\n")
    assert r.returncode == 0
    assert "line1\nline2\n" in (tmp_path / "bus/threads/t1.md").read_text()


def test_say_bad_thread_exits_1(tmp_path):
    r = run("agent-say", "--to", "claude", "--thread", "Bad Id", "x",
            root=tmp_path, env={"AGENT_NAME": "grok"})
    assert r.returncode == 1
    assert r.stderr.strip()


def test_human_say_posts_as_the_person(tmp_path):
    r = run("human-say", "--to", "claude", "--thread", "t1", "--status", "open", "go",
            root=tmp_path, env={"AGENT_NAME": "grok"})
    assert r.returncode == 0
    assert " · pat → claude · thread t1 · open\ngo\n" in (tmp_path / "bus/threads/t1.md").read_text()


def test_inbox_prints_and_marks_read(tmp_path):
    run("agent-say", "--to", "claude", "--thread", "t1", "one", root=tmp_path, env={"AGENT_NAME": "grok"})
    r = run("agent-inbox", "claude", "--peek", root=tmp_path)
    assert "grok → claude" in r.stdout and "one" in r.stdout
    r = run("agent-inbox", "claude", root=tmp_path)
    assert "one" in r.stdout
    r = run("agent-inbox", "claude", root=tmp_path)
    assert r.stdout == ""


def test_inbox_wait_returns_immediately_when_unread(tmp_path):
    run("agent-say", "--to", "claude", "--thread", "t1", "one", root=tmp_path, env={"AGENT_NAME": "grok"})
    t = time.time()
    r = run("agent-inbox", "claude", "--wait", root=tmp_path, timeout=5)
    assert r.returncode == 0 and "one" in r.stdout
    assert time.time() - t < 2


def _wait_for(path, secs=5):
    end = time.time() + secs
    while time.time() < end:
        if path.exists():
            return True
        time.sleep(0.05)
    return False


def _pid_text(pidfile):
    try:
        return pidfile.read_text().strip()
    except FileNotFoundError:
        return ""


def test_inbox_wait_wakes_on_append(tmp_path):
    env = {**os.environ, "AGENTS_ROOT": str(tmp_path), "AGENT_NAME": "grok"}
    p = subprocess.Popen(
        ["sh", "-c", "sleep 1; %s --to claude --thread fresh woke" % (BIN / "agent-say")],
        env=env)
    t = time.time()
    r = run("agent-inbox", "claude", "--wait", root=tmp_path, timeout=5)
    p.wait()
    assert r.returncode == 0 and "woke" in r.stdout
    assert 0.5 < time.time() - t < 3


def test_inbox_wait_wakes_on_append_to_existing_thread(tmp_path):
    run("agent-say", "--to", "grok", "--thread", "t1", "first", root=tmp_path, env={"AGENT_NAME": "claude"})
    env = {**os.environ, "AGENTS_ROOT": str(tmp_path), "AGENT_NAME": "grok"}
    p = subprocess.Popen(
        ["sh", "-c", "sleep 1; %s --to claude --thread t1 second" % (BIN / "agent-say")], env=env)
    r = run("agent-inbox", "claude", "--wait", root=tmp_path, timeout=5)
    p.wait()
    assert "second" in r.stdout


def test_watcher_pidfile_lifecycle(tmp_path):
    e = {**os.environ, "AGENTS_ROOT": str(tmp_path)}
    pidfile = tmp_path / "claude" / "watcher.pid"
    p = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e,
                         stdout=subprocess.PIPE, text=True)
    assert _wait_for(pidfile)
    assert int(pidfile.read_text()) == p.pid
    p.terminate()
    p.wait(timeout=5)
    assert not pidfile.exists()
    # normal exit path
    p = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
    assert _wait_for(pidfile)
    run("agent-say", "--to", "claude", "--thread", "t1", "x", root=tmp_path, env={"AGENT_NAME": "grok"})
    p.wait(timeout=5)
    assert p.returncode == 0
    assert not pidfile.exists()


def test_no_pidfile_for_other_agents(tmp_path):
    run("agent-say", "--to", "grok", "--thread", "t1", "x", root=tmp_path, env={"AGENT_NAME": "claude"})
    run("agent-inbox", "grok", "--wait", root=tmp_path)
    assert not (tmp_path / "grok" / "watcher.pid").exists()


def test_log_merges_and_filters(tmp_path):
    for ts, th, who in (("2026-10-29 09:00", "b", "grok"), ("2026-10-29 08:00", "a", "claude"),
                        ("2026-10-29 10:00", "a", "grok")):
        run("agent-say", "--to", "all", "--thread", th, "m-" + ts[-5:], root=tmp_path,
            env={"AGENT_NAME": who, "AGENTBUS_NOW": ts})
    r = run("agent-log", root=tmp_path)
    assert r.stdout.index("m-08:00") < r.stdout.index("m-09:00") < r.stdout.index("m-10:00")
    r = run("agent-log", "--since", "2026-10-29 09:00", root=tmp_path)
    assert "m-08:00" not in r.stdout and "m-09:00" in r.stdout
    r = run("agent-log", "--thread", "a", root=tmp_path)
    assert "m-09:00" not in r.stdout and "m-10:00" in r.stdout


def test_inbox_second_watcher_keeps_its_pidfile(tmp_path):
    e = {**os.environ, "AGENTS_ROOT": str(tmp_path)}
    pidfile = tmp_path / "claude" / "watcher.pid"
    p1 = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
    assert _wait_for(pidfile)
    p2 = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
    deadline = time.time() + 5
    while time.time() < deadline and _pid_text(pidfile) != str(p2.pid):
        time.sleep(0.05)
    assert _pid_text(pidfile) == str(p2.pid)
    p1.terminate()
    p1.wait(timeout=5)
    assert _pid_text(pidfile) == str(p2.pid)
    p2.terminate()
    p2.wait(timeout=5)
    assert not pidfile.exists()


def test_inbox_sighup_cleans_pidfile(tmp_path):
    e = {**os.environ, "AGENTS_ROOT": str(tmp_path)}
    pidfile = tmp_path / "claude" / "watcher.pid"
    p = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
    assert _wait_for(pidfile)
    p.send_signal(1)
    p.wait(timeout=5)
    assert not pidfile.exists()


def test_human_say_checks_registry(tmp_path):
    assert run("human-say", "--to", "nobody", "--thread", "t1", "x", root=tmp_path).returncode == 2
    assert run("human-say", "--to", "claude", "--thread", "t1", "x", root=tmp_path).returncode == 0
    fresh = tmp_path / "fresh"
    fresh.mkdir()
    r = run("agent-say", "--to", "claude", "--thread", "t1", "x", root=fresh, env={"NO_REGISTRY": "1", "AGENT_NAME": "grok"})
    assert r.returncode == 2 and "registry" in r.stderr


def test_inbox_wait_writes_delivered_json(tmp_path):
    run("agent-say", "--to", "claude", "--thread", "t1", "one", root=tmp_path, env={"AGENT_NAME": "grok"})
    run("agent-say", "--to", "claude", "--thread", "t2", "two", root=tmp_path, env={"AGENT_NAME": "grok"})
    t = time.time()
    r = run("agent-inbox", "claude", "--wait", root=tmp_path, timeout=5)
    assert r.returncode == 0
    d = json.loads((tmp_path / "claude" / "delivered.json").read_text())
    assert sorted(d["keys"]) == ["t1:0", "t2:0"]
    assert all(t - 1 <= v <= time.time() + 1 for v in d["keys"].values())


def test_inbox_wait_after_blocking_writes_delivered_json(tmp_path):
    env = {**os.environ, "AGENTS_ROOT": str(tmp_path), "AGENT_NAME": "grok"}
    p = subprocess.Popen(
        ["sh", "-c", "sleep 1; %s --to claude --thread fresh woke" % (BIN / "agent-say")], env=env)
    r = run("agent-inbox", "claude", "--wait", root=tmp_path, timeout=5)
    p.wait()
    d = json.loads((tmp_path / "claude" / "delivered.json").read_text())
    assert list(d["keys"]) == ["fresh:0"]


def test_peek_wait_records_no_delivery(tmp_path):
    run("agent-say", "--to", "claude", "--thread", "t1", "one", root=tmp_path, env={"AGENT_NAME": "grok"})
    r = run("agent-inbox", "claude", "--wait", "--peek", root=tmp_path, timeout=5)
    assert "one" in r.stdout
    assert not (tmp_path / "claude" / "delivered.json").exists()


def test_delivery_recorded_before_pidfile_removed(tmp_path):
    """Watch the pid file vanish; delivered.json must already exist at that moment."""
    e = {k: v for k, v in os.environ.items() if k != "AGENT_NAME"}
    e["AGENTS_ROOT"] = str(tmp_path)
    pidfile = tmp_path / "claude" / "watcher.pid"
    deliv = tmp_path / "claude" / "delivered.json"
    p = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e,
                         stdout=subprocess.PIPE, text=True)
    assert _wait_for(pidfile)
    run("agent-say", "--to", "claude", "--thread", "t1", "x", root=tmp_path, env={"AGENT_NAME": "grok"})
    bad = False
    end = time.time() + 5
    while time.time() < end:
        if not pidfile.exists():
            bad = not deliv.exists()
            break
    p.wait(timeout=5)
    assert not bad and deliv.exists()


def test_delivery_merges_and_migrates_old_form(tmp_path):
    (tmp_path / "claude").mkdir()
    (tmp_path / "claude" / "delivered.json").write_text(
        json.dumps({"ts": time.time(), "keys": ["old:0"]}))
    run("agent-say", "--to", "claude", "--thread", "t1", "one", root=tmp_path, env={"AGENT_NAME": "grok"})
    run("agent-inbox", "claude", "--wait", root=tmp_path, timeout=5)
    d = json.loads((tmp_path / "claude" / "delivered.json").read_text())
    assert sorted(d["keys"]) == ["old:0", "t1:0"]


REARM = "Re-arm: run 'agent-inbox claude --wait' as a background Bash command."


def test_inbox_shows_answer_already_given(tmp_path):
    """After an on-call takeover the live watcher still delivers the message; the answer shows."""
    env = {"AGENTBUS_NOW": "2026-10-29 23:56"}
    run("agent-say", "--to", "claude", "--thread", "t1", "ping", root=tmp_path,
        env={**env, "AGENT_NAME": "grok"})
    run("agent-say", "--to", "grok", "--thread", "t1", "--status", "taken", "Taken by on-call",
        root=tmp_path, env={**env, "AGENT_NAME": "claude-oncall"})
    run("agent-say", "--to", "grok", "--thread", "t1", "--status", "answered", "pong\nmore",
        root=tmp_path, env={**env, "AGENT_NAME": "claude-oncall"})
    r = run("agent-inbox", "claude", "--wait", root=tmp_path, timeout=5)
    lines = r.stdout.splitlines()
    assert "Already taken by claude-oncall at 23:56 on thread t1: Taken by on-call" in lines
    assert "Already answered by claude-oncall at 23:56 on thread t1: pong" in lines
    assert not [l for l in lines if l.startswith("Reply:")]
    assert "No reply needed: every message above was already answered or taken." in lines
    assert lines[-1] == REARM


def test_inbox_footer_reply_per_sender_thread_and_rearm(tmp_path):
    run("agent-say", "--to", "claude", "--thread", "t1", "a", root=tmp_path, env={"AGENT_NAME": "grok"})
    run("agent-say", "--to", "claude", "--thread", "t1", "b", root=tmp_path, env={"AGENT_NAME": "grok"})
    run("agent-say", "--to", "claude", "--thread", "t2", "c", root=tmp_path, env={"AGENT_NAME": "gemini"})
    peek = run("agent-inbox", "claude", "--peek", root=tmp_path).stdout
    assert "Reply:" not in peek and "Re-arm" not in peek
    lines = run("agent-inbox", "claude", root=tmp_path).stdout.splitlines()
    assert lines[-3:] == [
        'Reply: AGENT_NAME=claude agent-say --to grok --thread t1 --status answered "<text>"',
        'Reply: AGENT_NAME=claude agent-say --to gemini --thread t2 --status answered "<text>"',
        REARM]
    run("agent-say", "--to", "grok", "--thread", "t3", "d", root=tmp_path, env={"AGENT_NAME": "gemini"})
    out = run("agent-inbox", "grok", root=tmp_path).stdout
    assert "Reply:" not in out and "Re-arm" not in out


def test_inbox_refuses_another_agents_inbox(tmp_path):
    run("agent-say", "--to", "claude", "--thread", "t1", "x", root=tmp_path, env={"AGENT_NAME": "grok"})
    for args in (("claude",), ("claude", "--wait"), ("claude", "--peek")):
        r = run("agent-inbox", *args, root=tmp_path, env={"AGENT_NAME": "claude-oncall"})
        assert r.returncode == 2 and r.stdout == "" and "own inbox" in r.stderr
    assert not (tmp_path / "claude" / "watcher.pid").exists()
    assert not (tmp_path / "claude" / "cursor.json").exists()
    r = run("agent-inbox", "claude-oncall", root=tmp_path, env={"AGENT_NAME": "claude-oncall"})
    assert r.returncode == 0
    r = run("agent-inbox", "claude", root=tmp_path)  # no AGENT_NAME: the live session
    assert r.returncode == 0 and "x" in r.stdout


def test_inbox_skips_unreadable_thread(tmp_path):
    run("agent-say", "--to", "claude", "--thread", "good", "fine", root=tmp_path, env={"AGENT_NAME": "grok"})
    (tmp_path / "bus" / "threads" / "bad.md").write_bytes(b"### \xff\xfe broken\n")
    r = run("agent-inbox", "claude", root=tmp_path)
    assert r.returncode == 0 and "fine" in r.stdout
    assert r.stderr.count("skipped unreadable thread bad") == 1
    run("agent-say", "--to", "claude", "--thread", "good", "again", root=tmp_path, env={"AGENT_NAME": "grok"})
    r = run("agent-inbox", "claude", "--wait", "--peek", root=tmp_path)
    assert r.returncode == 0 and "again" in r.stdout and r.stderr.count("bad") == 1


def replies(out):
    return [l for l in out.splitlines() if l.startswith("Reply:")]


def test_reply_lines_only_for_open_messages(tmp_path):
    run("agent-say", "--to", "claude", "--thread", "t1", "--status", "answered", "thanks",
        root=tmp_path, env={"AGENT_NAME": "grok"})
    run("agent-say", "--to", "claude", "--thread", "t2", "--status", "closed", "done",
        root=tmp_path, env={"AGENT_NAME": "gemini"})
    out = run("agent-inbox", "claude", root=tmp_path).stdout
    assert "thanks" in out and replies(out) == []
    run("agent-say", "--to", "claude", "--thread", "t1", "one more", root=tmp_path, env={"AGENT_NAME": "grok"})
    out = run("agent-inbox", "claude", root=tmp_path).stdout
    assert replies(out) == [
        'Reply: AGENT_NAME=claude agent-say --to grok --thread t1 --status answered "<text>"']


def test_unrelated_answer_keeps_reply_fallback_answer_drops_it(tmp_path):
    reg = _reg(("claude", "claude-oncall", "pat", "grok", "gemini"))
    reg["claude"]["fallback"] = "claude-oncall"
    (tmp_path / "registry.json").write_text(json.dumps(reg))
    run("agent-say", "--to", "claude", "--thread", "t1", "q1", root=tmp_path, env={"AGENT_NAME": "grok"})
    run("agent-say", "--to", "pat", "--thread", "t1", "--status", "answered", "side talk",
        root=tmp_path, env={"AGENT_NAME": "gemini"})
    out = run("agent-inbox", "claude", "--peek", root=tmp_path).stdout
    assert "Later on thread t1" in out and "Already" not in out
    out = run("agent-inbox", "claude", root=tmp_path).stdout
    assert len(replies(out)) == 1
    run("agent-say", "--to", "claude", "--thread", "t2", "q2", root=tmp_path, env={"AGENT_NAME": "grok"})
    run("agent-say", "--to", "pat", "--thread", "t2", "--status", "answered", "covered it",
        root=tmp_path, env={"AGENT_NAME": "claude-oncall"})
    out = run("agent-inbox", "claude", root=tmp_path).stdout
    assert "Already answered by claude-oncall" in out and replies(out) == []


def _alive(pid):
    try:
        os.kill(pid, 0)
    except OSError:
        return False
    r = subprocess.run(["ps", "-o", "stat=", "-p", str(pid)], capture_output=True, text=True)
    return bool(r.stdout.strip()) and not r.stdout.strip().startswith("Z")


def _wait_gone(pid, secs=5):
    end = time.time() + secs
    while time.time() < end:
        if not _alive(pid):
            return True
        time.sleep(0.05)
    return False


def test_new_watcher_terminates_live_old_one(tmp_path):
    e = {**os.environ, "AGENTS_ROOT": str(tmp_path)}
    pidfile = tmp_path / "claude" / "watcher.pid"
    p1 = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
    assert _wait_for(pidfile)
    p2 = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
    try:
        assert _wait_gone(p1.pid)
        end = time.time() + 5
        while time.time() < end and _pid_text(pidfile) != str(p2.pid):
            time.sleep(0.05)
        assert _pid_text(pidfile) == str(p2.pid)
        assert p2.poll() is None
    finally:
        p2.terminate()
        p2.wait(timeout=5)
        p1.wait(timeout=5)


def test_new_watcher_leaves_unrelated_live_pid_alone(tmp_path):
    e = {**os.environ, "AGENTS_ROOT": str(tmp_path)}
    pidfile = tmp_path / "claude" / "watcher.pid"
    pidfile.parent.mkdir(parents=True)
    other = subprocess.Popen(["sleep", "60"])
    pidfile.write_text("%d\n" % other.pid)
    p = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
    try:
        end = time.time() + 5
        while time.time() < end and _pid_text(pidfile) != str(p.pid):
            time.sleep(0.05)
        assert _pid_text(pidfile) == str(p.pid)
        assert other.poll() is None
    finally:
        p.terminate()
        p.wait(timeout=5)
        other.kill()
        other.wait()


def test_new_watcher_leaves_inbox_for_other_agent_alone(tmp_path):
    e = {**os.environ, "AGENTS_ROOT": str(tmp_path)}
    pidfile = tmp_path / "claude" / "watcher.pid"
    g = subprocess.Popen([str(BIN / "agent-inbox"), "grok", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
    try:
        time.sleep(0.5)
        pidfile.parent.mkdir(parents=True, exist_ok=True)
        pidfile.write_text("%d\n" % g.pid)
        p = subprocess.Popen([str(BIN / "agent-inbox"), "claude", "--wait"], env=e, stdout=subprocess.PIPE, text=True)
        end = time.time() + 5
        while time.time() < end and _pid_text(pidfile) != str(p.pid):
            time.sleep(0.05)
        assert _pid_text(pidfile) == str(p.pid)
        assert g.poll() is None
        p.terminate()
        p.wait(timeout=5)
    finally:
        g.terminate()
        g.wait(timeout=5)


def test_watcher_exits_when_parent_dies_without_consuming(tmp_path):
    pidfile = tmp_path / "claude" / "watcher.pid"
    env = {**os.environ, "AGENTS_ROOT": str(tmp_path)}
    # a shell that backgrounds the watcher and lingers, then is killed, orphaning it
    sh = subprocess.Popen(["sh", "-c", "%s claude --wait >/dev/null 2>&1 </dev/null & echo $!; sleep 60" % (BIN / "agent-inbox")],
                          env=env, stdout=subprocess.PIPE, text=True)
    pid = int(sh.stdout.readline().strip())
    try:
        assert _wait_for(pidfile)
        assert _alive(pid)
        sh.kill()
        sh.wait()
        assert _wait_gone(pid, 12)
        assert not pidfile.exists()
        run("agent-say", "--to", "claude", "--thread", "t1", "kept", root=tmp_path, env={"AGENT_NAME": "grok"})
        r = run("agent-inbox", "claude", root=tmp_path)
        assert "kept" in r.stdout
    finally:
        if _alive(pid):
            os.kill(pid, 9)


def _live_registry(root):
    reg = _reg(("claude", "claude-oncall", "pat", "grok"))
    reg["claude2"] = dict(reg["claude"], wake="live")
    (Path(root) / "registry.json").write_text(json.dumps(reg))


def test_second_live_session_has_its_own_delivery_and_footer(tmp_path):
    _live_registry(tmp_path)
    run("agent-say", "--to", "claude2", "--thread", "t1", "take this", root=tmp_path,
        env={"AGENT_NAME": "claude"})
    r = run("agent-inbox", "claude2", "--wait", root=tmp_path, timeout=5)
    assert r.returncode == 0
    assert "take this" in r.stdout
    assert 'Reply: AGENT_NAME=claude2 agent-say --to claude --thread t1' in r.stdout
    assert r.stdout.strip().endswith(
        "Re-arm: run 'agent-inbox claude2 --wait' as a background Bash command.")
    d = json.loads((tmp_path / "claude2" / "delivered.json").read_text())
    assert list(d["keys"]) == ["t1:0"]
    assert not (tmp_path / "claude" / "delivered.json").exists()
    assert run("agent-inbox", "claude", "--peek", root=tmp_path).stdout == ""


def test_second_live_session_keeps_its_own_watcher_pid(tmp_path):
    _live_registry(tmp_path)
    e = {k: v for k, v in os.environ.items() if k not in ("AGENT_NAME", "AGENTBUS_NOW")}
    e["AGENTS_ROOT"] = str(tmp_path)
    p = subprocess.Popen([str(BIN / "agent-inbox"), "claude2", "--wait"], env=e,
                         stdout=subprocess.PIPE, text=True)
    try:
        pidfile = tmp_path / "claude2" / "watcher.pid"
        end = time.time() + 5
        while time.time() < end and not pidfile.exists():
            time.sleep(0.05)
        assert pidfile.read_text().strip() == str(p.pid)
        assert not (tmp_path / "claude" / "watcher.pid").exists()
    finally:
        p.terminate()
        p.wait(timeout=5)
