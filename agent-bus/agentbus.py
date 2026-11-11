"""agentbus: plain-text message threads under ~/agents/bus/threads/.

Each thread is a markdown file. Each message is a block opened by a header line

    ### YYYY-MM-DD HH:MM · sender → to · thread <id> · <status>

followed by the body. Body lines that start with "### " are written with a
leading backslash and unescaped on read, so a body can never forge a header.
Appends hold an exclusive flock on the thread file.

Tamper evidence: every append also writes one line to
<root>/bus/chain/<thread>.jsonl under the same lock, {"i", "h", "c"}: the
message index, the SHA-256 of the parsed message, and a chain value
sha256(previous c + h). verify() replays a thread against its chain and names
the first message that was altered, removed, or written around agentbus.
The chain catches edits after the fact and does not stop them. An agent that
rewrote both files consistently would pass verify, so pair the bus with a
PreToolUse guard that refuses writes under <root>/bus from anything but these
commands (the recipe says how).
"""
import hashlib
import fcntl
import json
import os
import re
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

STATUSES = ("open", "answered", "taken", "parked", "closed")
_THREAD_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")
_HEADER_RE = re.compile(
    r"^### (\d{4}-\d{2}-\d{2} \d{2}:\d{2}) · (\S+) → (\S+) · thread (\S+) · (\S+)$"
)
_ESCAPED_RE = re.compile(r"^(\\*)### ")


@dataclass
class Message:
    ts: str
    sender: str
    to: str
    thread: str
    status: str
    body: str
    index: int


def root() -> Path:
    return Path(os.environ.get("AGENTS_ROOT") or os.path.expanduser("~/agents"))


def registry() -> dict:
    """Agents from <root>/registry.json. Relative homes resolve against the root."""
    path = root() / "registry.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    out = {}
    for name, ent in data.items():
        ent = dict(ent)
        home = ent.get("home") or ""
        if home and not os.path.isabs(home):
            ent["home"] = str(root() / home)
        out[name] = ent
    return out


def live_session(agent: str) -> bool:
    """True for an agent that is a live interactive session: a registry entry
    with wake "live". These keep a watcher pid and a delivered file, and their
    inbox output ends with reply and re-arm lines."""
    try:
        return registry().get(agent, {}).get("wake") == "live"
    except (OSError, ValueError, AttributeError, TypeError):
        return False


def human() -> str:
    """The person's name on the bus: the registry entry marked "human": true.
    Empty when no entry is marked or the registry cannot be read. Agents may
    not post under this name; human-say does."""
    try:
        for name, ent in registry().items():
            if ent.get("human") is True:
                return name
    except (OSError, ValueError, AttributeError, TypeError):
        pass
    return ""


def valid_thread(thread: str) -> bool:
    return isinstance(thread, str) and _THREAD_RE.fullmatch(thread) is not None


def _check_thread(thread: str) -> None:
    if not valid_thread(thread):
        raise ValueError("bad thread id: %r" % (thread,))


def _thread_path(thread: str) -> Path:
    _check_thread(thread)
    return root() / "bus" / "threads" / (thread + ".md")


def _now() -> str:
    frozen = os.environ.get("AGENTBUS_NOW")
    if frozen:
        return frozen
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def _escape(body: str) -> str:
    out = []
    for line in body.split("\n"):
        out.append("\\" + line if _ESCAPED_RE.match(line) else line)
    return "\n".join(out)


def _unescape(lines) -> str:
    out = []
    for line in lines:
        m = _ESCAPED_RE.match(line)
        out.append(line[1:] if m and m.group(1) else line)
    return "\n".join(out)


def format_message(m: Message) -> str:
    """The block as it appears in a thread file: header, body, blank line."""
    header = "### %s · %s → %s · thread %s · %s" % (m.ts, m.sender, m.to, m.thread, m.status)
    return header + "\n" + _escape(m.body) + "\n\n"


def append(thread: str, sender: str, to: str, body: str, status: str = "open") -> Message:
    _check_thread(thread)
    if status not in STATUSES:
        raise ValueError("bad status: %r" % (status,))
    for name, val in (("sender", sender), ("to", to)):
        if not val or re.search(r"\s", val):
            raise ValueError("bad %s: %r" % (name, val))
    path = _thread_path(thread)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = body.strip("\n")
    ts = _now()
    block = format_message(Message(ts, sender, to, thread, status, body, -1))
    with open(path, "a+", encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_EX)
        try:
            f.seek(0)
            index = sum(1 for line in f if _HEADER_RE.match(line.rstrip("\n")))
            f.write(block)
            f.flush()
            os.fsync(f.fileno())
            _chain_append(thread, Message(ts, sender, to, thread, status, body, index))
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return Message(ts, sender, to, thread, status, body, index)


def _chain_path(thread: str) -> Path:
    _check_thread(thread)
    return root() / "bus" / "chain" / (thread + ".jsonl")


def message_hash(m: Message) -> str:
    canon = json.dumps([m.ts, m.sender, m.to, m.thread, m.status, m.body],
                       ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(canon.encode("utf-8")).hexdigest()


def _link(prev: str, h: str) -> str:
    return hashlib.sha256((prev + h).encode("ascii")).hexdigest()


def _load_chain(thread: str) -> list:
    path = _chain_path(thread)
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except ValueError:
                out.append({})
    return out


# ---- signatures ----
# Each agent has an Ed25519 key pair under <root>/keys: <agent> (private, 0600)
# and <agent>.pub. allowed_signers lists every public key against its agent
# name. append signs the message's chain link with the sender's key and stores
# the signature in the chain entry as "s"; the link covers the message and
# everything before it on the thread, so a signature also fixes the position.
# ssh-keygen -Y does the signing and checking; no crypto code lives here.
#
# What this does and does not prove. Every key is a file readable by this
# machine's one user, so a process with a full shell can sign as any agent. A
# signature shows the message went through agentbus with that sender's key; it
# catches a message written into a thread file by hand, a header naming a
# sender whose key did not sign it, and a signed message altered later.
#
# Signing is on once <root>/keys/cutover.json exists (keys_init writes it). It
# records how many messages each thread held at that moment: those read as
# "old", and any later message without a signature reads as "unsigned".

SIG_NAMESPACE = "agentbus"
_SSH_KEYGEN = "/usr/bin/ssh-keygen"


def _keys_dir() -> Path:
    return root() / "keys"


def _key_path(agent: str) -> Path:
    if not valid_thread(agent):
        raise ValueError("bad agent name: %r" % (agent,))
    return _keys_dir() / agent


def signing_enabled() -> bool:
    return (_keys_dir() / "cutover.json").exists()


def _cutover() -> dict:
    """Thread name -> message count when signing was switched on."""
    try:
        with open(_keys_dir() / "cutover.json", encoding="utf-8") as f:
            data = json.load(f)
        t = data.get("threads")
        return t if isinstance(t, dict) else {}
    except (OSError, ValueError, AttributeError):
        return {}


def _sign(sender: str, link: str) -> str:
    """The sender's signature over a chain link, or "" with no key or on any failure.

    Never raises: a message is posted unsigned sooner than not posted.
    """
    try:
        key = _key_path(sender)
        if not key.exists():
            return ""
        r = subprocess.run([_SSH_KEYGEN, "-q", "-Y", "sign", "-f", str(key), "-n", SIG_NAMESPACE],
                           input=(link + "\n").encode("ascii"), capture_output=True, timeout=10)
        return r.stdout.decode("ascii").strip() if r.returncode == 0 else ""
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        return ""


def _check_sig(sender: str, link: str, sig: str) -> bool:
    signers = _keys_dir() / "allowed_signers"
    if not sig or not link or not signers.exists():
        return False
    tmp = None
    try:
        fd, tmp = tempfile.mkstemp(prefix="agentbus-sig-")
        with os.fdopen(fd, "w", encoding="ascii") as f:
            f.write(sig + "\n")
        r = subprocess.run([_SSH_KEYGEN, "-Y", "verify", "-f", str(signers), "-I", sender,
                            "-n", SIG_NAMESPACE, "-s", tmp],
                           input=(link + "\n").encode("ascii"), capture_output=True, timeout=10)
        return r.returncode == 0
    except (OSError, ValueError, UnicodeError, subprocess.SubprocessError):
        return False
    finally:
        if tmp:
            try:
                os.unlink(tmp)
            except OSError:
                pass


def sig_states(thread: str, only=None) -> dict:
    """Message index -> "signed", "old", "unsigned" or "bad".

    signed: the chain entry matches the message and its place on the thread, and
    the signature is the header's sender's. bad: a signature is there and that
    does not hold. old: no signature, posted before signing was switched on.
    unsigned: no signature, posted after. `only` limits the answer (and the
    signature checks) to those indexes.
    """
    msgs = read_thread_safe(thread)
    entries = _load_chain(thread)
    cut = _cutover().get(thread, 0)
    try:
        cut = int(cut)
    except (TypeError, ValueError):
        cut = 0
    out, prev = {}, ""
    for i, m in enumerate(msgs):
        e = entries[i] if i < len(entries) else {}
        h, c, s = e.get("h", ""), e.get("c", ""), e.get("s", "")
        intact = e.get("i") == i and h == message_hash(m) and bool(c) and c == _link(prev, h)
        prev = c if isinstance(c, str) else ""
        if only is not None and i not in only:
            continue
        if s:
            out[i] = "signed" if intact and isinstance(s, str) and _check_sig(m.sender, c, s) else "bad"
        else:
            out[i] = "old" if i < cut else "unsigned"
    return out


def keys_init() -> list:
    """Make a key for every registry agent that lacks one, rewrite allowed_signers
    from the public keys on disk, and switch signing on if it is not yet.

    Safe to run again after adding an agent. Returns one line per thing done.
    """
    kd = _keys_dir()
    kd.mkdir(parents=True, exist_ok=True)
    os.chmod(kd, 0o700)
    done = []
    for agent in sorted(registry()):
        key = _key_path(agent)
        if key.exists() and key.with_name(agent + ".pub").exists():
            continue
        r = subprocess.run([_SSH_KEYGEN, "-q", "-t", "ed25519", "-N", "", "-C", "bus:" + agent,
                            "-f", str(key)], capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            raise RuntimeError("ssh-keygen failed for %s: %s" % (agent, r.stderr.strip()))
        done.append("key made for %s" % agent)
    lines = []
    for pub in sorted(kd.glob("*.pub")):
        parts = pub.read_text(encoding="ascii").split()
        if len(parts) >= 2 and valid_thread(pub.stem):
            lines.append('%s namespaces="%s" %s %s' % (pub.stem, SIG_NAMESPACE, parts[0], parts[1]))
    fd, tmp = tempfile.mkstemp(dir=str(kd), prefix=".signers-")
    with os.fdopen(fd, "w", encoding="ascii") as f:
        f.write("\n".join(lines) + "\n")
    os.chmod(tmp, 0o644)
    os.replace(tmp, kd / "allowed_signers")
    done.append("allowed_signers lists %d key(s)" % len(lines))
    if not signing_enabled():
        counts = {t: len(read_thread_safe(t)) for t in threads()}
        fd, tmp = tempfile.mkstemp(dir=str(kd), prefix=".cutover-")
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            json.dump({"ts": _now(), "threads": counts}, f, indent=1, sort_keys=True)
        os.chmod(tmp, 0o644)
        os.replace(tmp, kd / "cutover.json")
        done.append("signing switched on; %d existing thread(s) recorded as old" % len(counts))
    return done


def _chain_append(thread: str, m: Message) -> None:
    """Caller holds the thread lock. The chain file has its own fsync."""
    path = _chain_path(thread)
    path.parent.mkdir(parents=True, exist_ok=True)
    entries = _load_chain(thread)
    prev = entries[-1].get("c", "") if entries else ""
    h = message_hash(m)
    entry = {"i": m.index, "h": h, "c": _link(prev, h)}
    sig = _sign(m.sender, entry["c"])
    if sig:
        entry["s"] = sig
    line = json.dumps(entry, separators=(",", ":"))
    with open(path, "a", encoding="utf-8") as f:
        f.write(line + "\n")
        f.flush()
        os.fsync(f.fileno())


def verify(thread: str) -> dict:
    """Replay a thread against its chain.

    state: ok; altered (message or chain entry at `at` no longer matches);
    unsealed (message at `at` and after were written without agentbus);
    missing (chain records messages from `at` on that the file no longer has).
    """
    msgs = read_thread(thread)
    entries = _load_chain(thread)
    prev = ""
    for i, m in enumerate(msgs):
        if i >= len(entries):
            return {"state": "unsealed", "count": len(msgs), "at": i,
                    "detail": "%d message(s) from #%d have no chain entry" % (len(msgs) - i, i)}
        e = entries[i]
        if e.get("i") != i or e.get("h") != message_hash(m):
            return {"state": "altered", "count": len(msgs), "at": i,
                    "detail": "message #%d does not match its chain entry" % i}
        if e.get("c") != _link(prev, e["h"]):
            return {"state": "altered", "count": len(msgs), "at": i,
                    "detail": "chain entry #%d was rewritten" % i}
        prev = e["c"]
    if len(entries) > len(msgs):
        return {"state": "missing", "count": len(msgs), "at": len(msgs),
                "detail": "chain records %d message(s) the file no longer has" % (len(entries) - len(msgs))}
    return {"state": "ok", "count": len(msgs), "at": None, "detail": ""}


def seal_existing() -> list:
    """One-time deploy step: chain every thread that has no chain file yet.

    Refuses once <root>/bus/chain/.sealed exists, so it can never be used later
    to bless a thread that was written around agentbus.
    """
    marker = root() / "bus" / "chain" / ".sealed"
    if marker.exists():
        raise RuntimeError("already sealed at %s; seal_existing is one-shot" % marker)
    sealed = []
    for t in threads():
        if _chain_path(t).exists():
            continue
        path = _thread_path(t)
        with open(path, "a+", encoding="utf-8") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                for m in read_thread_unlocked(path):
                    _chain_append(t, m)
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        sealed.append(t)
    marker.parent.mkdir(parents=True, exist_ok=True)
    marker.write_text(_now() + "\n", encoding="utf-8")
    return sealed


def read_thread(thread: str) -> list:
    path = _thread_path(thread)
    if not path.exists():
        return []
    with open(path, encoding="utf-8") as f:
        fcntl.flock(f, fcntl.LOCK_SH)
        try:
            text = f.read()
        finally:
            fcntl.flock(f, fcntl.LOCK_UN)
    return _parse(text)


def read_thread_unlocked(path: Path) -> list:
    """Parse a thread file without taking a lock (the caller holds one)."""
    with open(path, encoding="utf-8") as f:
        return _parse(f.read())


def _parse(text: str) -> list:
    msgs = []
    cur = None
    lines = []
    for line in text.split("\n"):
        m = _HEADER_RE.match(line)
        if m:
            if cur is not None:
                msgs.append(Message(*cur, _unescape(lines).strip("\n"), len(msgs)))
            cur = m.groups()
            lines = []
        elif cur is not None:
            lines.append(line)
    if cur is not None:
        msgs.append(Message(*cur, _unescape(lines).strip("\n"), len(msgs)))
    return msgs


def threads() -> list:
    d = root() / "bus" / "threads"
    if not d.is_dir():
        return []
    return sorted(p.stem for p in d.glob("*.md") if valid_thread(p.stem))


def _cursor_path(agent: str) -> Path:
    if not valid_thread(agent):
        raise ValueError("bad agent name: %r" % (agent,))
    return root() / agent / "cursor.json"


def _load_cursor(agent: str) -> dict:
    try:
        with open(_cursor_path(agent), encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


def read_thread_safe(thread: str, errors=None) -> list:
    """read_thread, but an unreadable file (non-UTF-8, I/O error) reads as empty.

    The failure is appended to errors, when given, as one line.
    """
    try:
        return read_thread(thread)
    except (OSError, ValueError) as e:
        if errors is not None:
            errors.append("%s: %s: %s" % (thread, type(e).__name__, e))
        return []


def unread(agent: str, errors=None) -> list:
    cursor = _load_cursor(agent)
    out = []
    for t in threads():
        last = cursor.get(t, -1)
        out.extend(m for m in read_thread_safe(t, errors) if m.to == agent and m.index > last)
    return out


# ---- done receipts ----
# A closing message can carry proof: trailer lines at the end of the body,
#     Receipt: <full commit sha> in <repo path>
#     Files: a.py, tests/b.py
# They are part of the body, so the hash chain covers them. make_receipt checks
# them before the message is posted; check_receipt checks them again on read,
# because a commit can vanish after the fact (a rebase, a deleted repo).

_RECEIPT_RE = re.compile(r"^Receipt: ([0-9a-f]{40}) in (\S.*)$", re.M)
_FILES_RE = re.compile(r"^Files: (.+)$", re.M)
# Git run on a path taken from a message body: no hooks, no fsmonitor, no pager.
_GIT_SAFE = ["-c", "core.hooksPath=/dev/null", "-c", "core.fsmonitor=false", "--no-pager"]


def _git(repo: str, *args) -> str:
    import subprocess
    r = subprocess.run(["git", "-C", repo] + _GIT_SAFE + list(args),
                       capture_output=True, text=True, timeout=10)
    if r.returncode != 0:
        raise ValueError((r.stderr.strip() or "git failed").splitlines()[0])
    return r.stdout


def _short_home(path: str) -> str:
    home = os.path.expanduser("~")
    return "~" + path[len(home):] if path == home or path.startswith(home + os.sep) else path


def _commit_check(repo: str, sha: str, files: list):
    """(full sha, problem or ''). Raises nothing."""
    path = os.path.realpath(os.path.expanduser(repo))
    if not os.path.isdir(path):
        return sha, "repo %s not found" % repo
    try:
        full = _git(path, "rev-parse", "--verify", "--quiet", sha + "^{commit}").strip()
    except (ValueError, OSError) as e:
        return sha, "commit %s not found in %s" % (sha[:12], repo)
    if not full:
        return sha, "commit %s not found in %s" % (sha[:12], repo)
    if files:
        try:
            changed = set(_git(path, "show", "--name-only", "--format=", full).split("\n"))
        except (ValueError, OSError) as e:
            return full, "cannot list files of %s: %s" % (full[:12], e)
        missing = [f for f in files if os.path.normpath(f) not in changed]
        if missing:
            return full, "not in commit %s: %s" % (full[:7], ", ".join(missing))
    return full, ""


def make_receipt(repo: str, sha: str, files: list) -> str:
    """Trailer text for a closing message; ValueError when the proof does not hold."""
    if not re.fullmatch(r"[0-9a-fA-F]{4,40}", sha or ""):
        raise ValueError("bad sha: %r" % (sha,))
    files = [f.strip() for f in files if f.strip()]
    for f in files:
        if "," in f or "\n" in f:
            raise ValueError("bad file name: %r" % (f,))
    full, problem = _commit_check(repo, sha.lower(), files)
    if problem:
        raise ValueError(problem)
    out = "Receipt: %s in %s" % (full, _short_home(os.path.realpath(os.path.expanduser(repo))))
    if files:
        out += "\nFiles: " + ", ".join(files)
    return out


def check_receipt(body: str):
    """None when the body carries no receipt, else {sha, repo, files, ok, problem}."""
    m = None
    for m in _RECEIPT_RE.finditer(body):
        pass
    if m is None:
        return None
    sha, repo = m.group(1), m.group(2).strip()
    files = []
    fm = None
    for fm in _FILES_RE.finditer(body):
        pass
    if fm is not None and fm.start() > m.start():
        files = [f.strip() for f in fm.group(1).split(",") if f.strip()]
    _, problem = _commit_check(repo, sha, files)
    return {"sha": sha, "repo": repo, "files": files, "ok": not problem, "problem": problem}


def first_line(body: str) -> str:
    return body.split("\n", 1)[0][:200]


def delivery_notes(agent: str, msgs: list):
    """What a reader of msgs needs beyond the blocks themselves.

    Returns (notes, replies). notes: one line per later message on a delivered
    thread that is not itself in msgs, so a message someone already answered is
    visibly answered. replies: the reply command for each distinct sender and
    thread with an open message to agent that is still unanswered. A later
    message answers m when it is answered or taken, comes from someone other than
    m's sender, and goes to m's sender or comes from agent's registry fallback.
    """
    try:
        fb = registry().get(agent, {}).get("fallback")
    except (OSError, ValueError, AttributeError, TypeError):
        fb = None

    def answers(x, m):
        return (x.status in ("answered", "taken") and x.sender != m.sender
                and (x.to == m.sender or (fb and x.sender == fb)))

    delivered = {(m.thread, m.index) for m in msgs}
    cache = {}
    notes, noted, replies, pairs = [], set(), [], set()
    for m in msgs:
        if m.thread not in cache:
            cache[m.thread] = read_thread_safe(m.thread)
        later = [x for x in cache[m.thread] if x.index > m.index]
        for x in later:
            k = (x.thread, x.index)
            if k in delivered or k in noted:
                continue
            noted.add(k)
            if answers(x, m):
                notes.append("Already %s by %s at %s on thread %s: %s" % (
                    x.status, x.sender, x.ts[11:16], x.thread, first_line(x.body)))
            else:
                notes.append("Later on thread %s at %s: %s → %s (%s): %s" % (
                    x.thread, x.ts[11:16], x.sender, x.to, x.status, first_line(x.body)))
        done = any(answers(x, m) for x in later)
        pair = (m.sender, m.thread)
        if m.status == "open" and m.to == agent and not done and pair not in pairs:
            pairs.add(pair)
            replies.append('Reply: AGENT_NAME=%s agent-say --to %s --thread %s --status answered "<text>"'
                           % (agent, m.sender, m.thread))
    return notes, replies


def mark_read(agent: str, msgs: list) -> None:
    path = _cursor_path(agent)
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name("cursor.lock")
    with open(lock, "a") as lf:
        fcntl.flock(lf, fcntl.LOCK_EX)
        try:
            cursor = _load_cursor(agent)
            for m in msgs:
                if m.index > cursor.get(m.thread, -1):
                    cursor[m.thread] = m.index
            fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".cursor-")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(cursor, f, indent=1, sort_keys=True)
            os.replace(tmp, path)
        finally:
            fcntl.flock(lf, fcntl.LOCK_UN)


# ---- helpers shared by the command-line tools ----

def cli_body(words: list) -> str:
    """Message text: the joined words, or stdin when there are none."""
    import sys
    return " ".join(words) if words else sys.stdin.read()


def cli_say(sender: str, argv: list, prog: str) -> int:
    """Shared body of agent-say and human-say. Returns an exit code."""
    import argparse
    import sys
    ap = argparse.ArgumentParser(prog=prog)
    ap.add_argument("--to", required=True)
    ap.add_argument("--thread", required=True)
    ap.add_argument("--status", default="open")
    ap.add_argument("--repo", help="done receipt: the git repo holding the commit")
    ap.add_argument("--sha", help="done receipt: the commit that did the work")
    ap.add_argument("--files", default="", help="done receipt: comma-separated paths the commit changed")
    ap.add_argument("message", nargs="*")
    a = ap.parse_args(argv)
    trailer = ""
    if a.repo or a.sha or a.files:
        if not (a.repo and a.sha):
            print("%s: a receipt needs both --repo and --sha" % prog, file=sys.stderr)
            return 2
        try:
            trailer = make_receipt(a.repo, a.sha, a.files.split(","))
        except ValueError as e:
            print("%s: receipt refused: %s" % (prog, e), file=sys.stderr)
            return 1
    try:
        known = registry()
    except (OSError, ValueError) as e:
        print("%s: cannot read registry (%s): %s" % (prog, root() / "registry.json", e), file=sys.stderr)
        return 2
    for label, name, extra in (("sender", sender, ()), ("recipient", a.to, ("all",))):
        if name not in known and name not in extra:
            print("%s: unknown %s %r (not in registry)" % (prog, label, name), file=sys.stderr)
            return 2
    try:
        body = cli_body(a.message)
        if trailer:
            body = body.rstrip("\n") + "\n\n" + trailer
        append(a.thread, sender, a.to, body, a.status)
    except ValueError as e:
        print("%s: %s" % (prog, e), file=sys.stderr)
        return 1
    return 0


def _main(argv) -> int:
    import sys
    if argv[:1] == ["verify"]:
        bad = 0
        for t in (argv[1:] or threads()):
            v = verify(t)
            print("%-60s %s%s" % (t, v["state"], (" (" + v["detail"] + ")") if v["detail"] else ""))
            bad += v["state"] != "ok"
        return 1 if bad else 0
    if argv == ["seal-existing"]:
        try:
            for t in seal_existing():
                print("sealed", t)
        except RuntimeError as e:
            print("agentbus: %s" % e, file=sys.stderr)
            return 2
        return 0
    if argv == ["keys-init"]:
        try:
            for line in keys_init():
                print(line)
        except (OSError, ValueError, RuntimeError, subprocess.SubprocessError) as e:
            print("agentbus: %s" % e, file=sys.stderr)
            return 2
        return 0
    if argv[:1] == ["sigs"]:
        if not signing_enabled():
            print("signing is off (no %s)" % (_keys_dir() / "cutover.json"))
            return 0
        worst = 0
        for t in (argv[1:] or threads()):
            st = sig_states(t)
            tally = {k: sum(1 for v in st.values() if v == k) for k in ("signed", "old", "unsigned", "bad")}
            flagged = ["#%d %s" % (i, v) for i, v in sorted(st.items()) if v in ("unsigned", "bad")]
            print("%-40s signed %d, old %d, unsigned %d, bad %d%s" % (
                t, tally["signed"], tally["old"], tally["unsigned"], tally["bad"],
                ("  [" + ", ".join(flagged) + "]") if flagged else ""))
            worst += tally["unsigned"] + tally["bad"]
        return 1 if worst else 0
    print("usage: agentbus.py verify [thread...] | seal-existing | keys-init | sigs [thread...]",
          file=sys.stderr)
    return 2


if __name__ == "__main__":
    import sys
    sys.exit(_main(sys.argv[1:]))
