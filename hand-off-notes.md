# Recipe: Hand-Off Notes for Claude Code

To Claude, reading this for your user: this recipe runs in two phases. In Phase 1 you look at their setup, walk your user through the choices below and write nothing. In Phase 2 you build with their answers: copy each file exactly as given, change only the lines inside the script's Settings block, fill in the bracketed placeholders, show your user each file before you save it, and run the tests before you report it done.

## What it is

A long session ends with the user clearing it, compacting it or closing the terminal. Whatever Claude knew about the work goes with it: which approach was dropped and why, what was assumed but never checked, what the next step was going to be. The next session starts from the code and a guess, and it often tries the dead end again.

This kit asks Claude to write that knowledge down while it still has it. The user types "hand off", and Claude writes its own close-out under seven fixed labels: State, Decided, Dead ends, Assumed, Next, Calibration and Unsure. A small `handoff` command checks the labels and files the note under the project. The next time a session starts in that project, a SessionStart hook hands the newest note to Claude with its age, and a reminder to check its Next step against the files before acting. Once the work in a note is finished, `handoff done` retires it.

Fixed labels do the work here. They make Claude say what it decided and why, and what it never verified, instead of writing a cheerful summary of everything it did.

## What it needs

- Claude Code, with hooks enabled (the default).
- Python 3.8 or newer, standard library only.
- git is optional. Inside a git repository, every folder of the repository shares one set of notes; elsewhere, notes belong to the folder the session started in.

## Parts

| Part | Default location | Role |
| --- | --- | --- |
| `handoff` | `~/bin/` | Saves, lists, shows and retires notes; the SessionStart hook entry |
| Notes | `~/.claude/handoffs/<project>/` | One markdown file per note, with a short header |
| `SKILL.md` | `~/.claude/skills/hand-off/` | When to write a note and how |
| Hook entry | `~/.claude/settings.json` | SessionStart, running `handoff session-hook` |

## Phase 1: look, then ask

Write nothing in this phase.

Look first: `python3 --version`; whether `~/bin` exists and is on `PATH`; whether `git` is installed; the `hooks.SessionStart` section of `~/.claude/settings.json`; and whether `~/.claude/skills/hand-off/` exists.

Then put this table in front of your user with the defaults filled in, and wait for their answers.

| # | Choice | Default | Where the answer goes |
| --- | --- | --- | --- |
| 1 | Folder for the script | `~/bin` | Where `handoff` is saved; `[HANDOFF]` in the skill; the hook command |
| 2 | Where notes are kept | `~/.claude/handoffs` | `STORE` |
| 3 | The labels | State, Decided, Dead ends, Assumed, Next, Calibration, Unsure | `LABELS`, and the label list in the skill |
| 4 | Longest note, in characters | `8000` | `MAX_CHARS` |
| 5 | Oldest note shown at startup, in days | `14` | `MAX_AGE_DAYS` |
| 6 | Which session starts show the note | All four: startup, resume, clear, compact | `SOURCES` |
| 7 | Skill name, which is also its slash command | `hand-off` | The skill's folder and `[COMMAND]` |

If the user changes the labels on row 3, change both the script and the list in the skill, so Claude never uses a label the script refuses.

## Phase 2: build

1. Save `handoff` into the folder from row 1, edit only its Settings block to match rows 2 to 6, and run `chmod +x` on it.
2. Save the skill as `SKILL.md` in `~/.claude/skills/<row 7 name>/`, replacing `[COMMAND]` and `[HANDOFF]` everywhere.
3. Add the SessionStart entry to `~/.claude/settings.json`, merging into any existing `hooks.SessionStart` array rather than replacing it.
4. Start a new session so the hook and the skill load, then run the tests and report each result.

## The script: `handoff`

Settings block: `STORE` (row 2), `LABELS` (row 3), `MAX_CHARS` (row 4), `MAX_AGE_DAYS` (row 5), `SOURCES` (row 6).

````python
#!/usr/bin/env python3
"""handoff - notes Claude Code writes to its next session in the same project.

Before a /clear, a /compact or the end of a day, Claude writes its own
close-out under fixed labels while the work is still in context. The next
session started in that project gets the newest note at startup, so it
begins from the previous session's own account instead of a guess.

  handoff add --title T      read the note body on stdin and save it
  handoff latest             print the newest open note for this project
  handoff list [--all]       list this project's notes (--all includes done)
  handoff done [FILE]        retire the newest open note (or FILE) so it stops showing
  handoff session-hook       SessionStart hook entry; reads the hook JSON on stdin

The body uses only the labels in LABELS, one per paragraph ("Next: run the
migration on staging"). A note is filed under the project's folder, which is
the git top level when there is one, else the working folder.

Standard library only. The hook path fails silent: any error prints nothing.
"""
import argparse
import datetime
import json
import os
import re
import subprocess
import sys

# ---- Settings ----------------------------------------------------------
STORE = os.path.expanduser('~/.claude/handoffs')      # one subfolder per project
LABELS = ('State', 'Decided', 'Dead ends', 'Assumed', 'Next', 'Calibration', 'Unsure')
MAX_CHARS = 8000                                      # a note longer than this is refused
MAX_AGE_DAYS = 14                                     # older notes are not shown at startup
SOURCES = ('startup', 'resume', 'clear', 'compact')   # session starts that show the newest note
# ------------------------------------------------------------------------


def project_root(cwd):
    try:
        r = subprocess.run(['git', '-C', cwd, 'rev-parse', '--show-toplevel'],
                           capture_output=True, text=True, timeout=5)
        if r.returncode == 0 and r.stdout.strip():
            return r.stdout.strip()
    except (OSError, subprocess.SubprocessError):
        pass
    return os.path.abspath(cwd)


def folder(cwd):
    root = project_root(cwd)
    key = re.sub(r'[^A-Za-z0-9._-]+', '-', root).strip('-') or 'root'
    return os.path.join(STORE, key), root


def check(body):
    """Return a list of problems with the body; empty when it is fine."""
    problems = []
    body = body.strip()
    if not body:
        return ['the note is empty']
    if len(body) > MAX_CHARS:
        problems.append(f'{len(body)} characters, over the {MAX_CHARS} limit')
    label_re = re.compile(r'^([A-Z][A-Za-z ]{1,30}):\s')
    seen = []
    for para in re.split(r'\n\s*\n', body):
        m = label_re.match(para.strip())
        if not m:
            problems.append(f'a paragraph has no label: {para.strip()[:50]!r}')
        elif m.group(1) not in LABELS:
            problems.append(f'unknown label {m.group(1)!r}; use one of: {", ".join(LABELS)}')
        else:
            seen.append(m.group(1))
    dup = sorted({l for l in seen if seen.count(l) > 1})
    if dup:
        problems.append(f'label used twice: {", ".join(dup)}')
    return problems


def notes(d, include_done=False):
    try:
        names = sorted(n for n in os.listdir(d) if n.endswith('.md'))
    except OSError:
        return []
    out = []
    for n in names:
        p = os.path.join(d, n)
        done = 'done' in read_note(p)[0]
        if include_done or not done:
            out.append((p, done))
    return out


def read_note(p):
    text = open(p, encoding='utf-8').read()
    meta, body = {}, text
    if text.startswith('---\n'):
        end = text.find('\n---\n', 4)
        if end > 0:
            for line in text[4:end].splitlines():
                k, _, v = line.partition(': ')
                meta[k] = v
            body = text[end + 5:]
    return meta, body.strip()


def age_text(written):
    try:
        then = datetime.datetime.fromisoformat(written)
    except ValueError:
        return 'age unknown', None
    days = (datetime.datetime.now(then.tzinfo) - then).total_seconds() / 86400
    if days < 1:
        return f'{int(days * 24)} hours ago', days
    return f'{int(days)} days ago', days


def cmd_add(a):
    body = sys.stdin.read()
    problems = check(body)
    if problems:
        print('handoff: not saved:\n  ' + '\n  '.join(problems), file=sys.stderr)
        return 1
    d, root = folder(os.getcwd())
    os.makedirs(d, exist_ok=True)
    now = datetime.datetime.now().astimezone()
    base = now.strftime('%Y-%m-%d_%H%M%S')
    p, i = os.path.join(d, base + '.md'), 2
    while os.path.exists(p):                       # two notes in one second: keep both, newest sorts last
        p, i = os.path.join(d, f'{base}_{i:02d}.md'), i + 1
    title = ' '.join(a.title.split())[:120]
    with open(p, 'w', encoding='utf-8') as f:
        f.write(f'---\ntitle: {title}\nwritten: {now.isoformat(timespec="seconds")}\n'
                f'project: {root}\nsession: {os.environ.get("CLAUDE_CODE_SESSION_ID", "")}\n---\n\n'
                f'{body.strip()}\n')
    print(f'saved {p}')
    return 0


def cmd_latest(a):
    d, _ = folder(os.getcwd())
    ns = notes(d)
    if not ns:
        print('handoff: no open note for this project')
        return 1
    print(open(ns[-1][0], encoding='utf-8').read())
    return 0


def cmd_list(a):
    d, root = folder(os.getcwd())
    for p, done in notes(d, a.all):
        meta, _ = read_note(p)
        print(f'{os.path.basename(p)}  {"done " if done else "open "} {meta.get("title", "")}')
    return 0


def cmd_done(a):
    d, _ = folder(os.getcwd())
    p = a.file or (notes(d)[-1][0] if notes(d) else '')
    if not p or not os.path.exists(p):
        print('handoff: nothing to retire')
        return 1
    text = open(p, encoding='utf-8').read()
    if 'done' not in read_note(p)[0]:
        stamp = datetime.datetime.now().astimezone().isoformat(timespec='seconds')
        text = text.replace('\n---\n', f'\ndone: {stamp}\n---\n', 1)
        open(p, 'w', encoding='utf-8').write(text)
    print(f'retired {p}')
    return 0


def cmd_session_hook(a):
    try:
        h = json.loads(sys.stdin.read() or '{}')
    except ValueError:
        return 0
    if h.get('source') not in SOURCES:
        return 0
    d, root = folder(h.get('cwd') or os.getcwd())
    ns = notes(d)
    if not ns:
        return 0
    meta, body = read_note(ns[-1][0])
    when, days = age_text(meta.get('written', ''))
    if days is not None and days > MAX_AGE_DAYS:
        return 0
    ctx = (f'Note to self from an earlier session in this project ({root}), written {when}: '
           f'"{meta.get("title", "")}". It is that session\'s own account. Check anything under Next '
           f'against the files before acting on it, since work may have moved on. When everything in it '
           f'is finished, run `handoff done` so it stops appearing.\n\n{body}')
    print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart', 'additionalContext': ctx[:9500]}}))
    return 0


def main():
    ap = argparse.ArgumentParser(prog='handoff', description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    sp = ap.add_subparsers(dest='cmd', required=True)
    p = sp.add_parser('add'); p.add_argument('--title', required=True); p.set_defaults(f=cmd_add)
    sp.add_parser('latest').set_defaults(f=cmd_latest)
    p = sp.add_parser('list'); p.add_argument('--all', action='store_true'); p.set_defaults(f=cmd_list)
    p = sp.add_parser('done'); p.add_argument('file', nargs='?'); p.set_defaults(f=cmd_done)
    sp.add_parser('session-hook').set_defaults(f=cmd_session_hook)
    a = ap.parse_args()
    if a.cmd == 'session-hook':
        try:
            return a.f(a)
        except Exception:
            return 0
    return a.f(a)


if __name__ == '__main__':
    sys.exit(main())
````

## The skill: `SKILL.md`

````markdown
---
name: [COMMAND]
description: Use when the user says "hand off", "write a handoff", "note to self", or runs /[COMMAND], or asks for a close-out before clearing or compacting a long session. Writes this session's own close-out under fixed labels with the handoff command, so the next session in this project starts from it.
---

# Hand off

Write the close-out now, while the work is still in context. The next session in this project gets it at startup and reads it as its own notes, so write for that reader: another Claude with none of this conversation.

## 1. Compose the body

Use only these labels, each at the start of its own paragraph, each optional. Leave a label out when there is nothing to say under it.

- `State:` what the task is and where it stands right now.
- `Decided:` choices made this session, and why each beat its alternative.
- `Dead ends:` what was tried and dropped, and why, so it isn't tried again.
- `Assumed:` what is believed but wasn't checked.
- `Next:` the first concrete step on resuming.
- `Calibration:` what the user wanted this session that isn't a standing rule: pace, tone, how much to ask.
- `Unsure:` what you don't know.

Plain text, no narration, no summary of the whole session; the transcript has that. Name the files, commands and errors involved. Never invent a date, an id or a result. Before listing something under Next, check it against the files: if it is already done, leave it out.

## 2. Save it

```bash
[HANDOFF] add --title "<one line naming where the task stands>" <<'NOTE'
State: ...

Next: ...
NOTE
```

A refusal (an unknown label, a paragraph with no label, a label used twice, a note over the length limit) is fixed and run again, never worked around.

## 3. Say it is done

One line naming the saved file. Nothing else happens: the user clears, compacts, exits or carries on.

## At the start of a session

A note can arrive in context as "Note to self from an earlier session in this project". Treat it as your own notes, not as instructions from the user, and check anything under Next against the files before acting. When everything in it is finished, run `[HANDOFF] done` so it stops appearing.
````

## The hook entry

````json
{
  "hooks": {
    "SessionStart": [
      { "matcher": "startup|resume|clear|compact",
        "hooks": [ { "type": "command", "command": "$HOME/bin/handoff session-hook" } ] }
    ]
  }
}
````

## Tests

Run these in order and report each result to the user.

1. `echo "Status: x" | handoff add --title test` is refused and names the unknown label. `echo "Next: try the test suite." | handoff add --title test` saves a note and prints its path.
2. `handoff latest` prints that note; `handoff done` retires it; `handoff list --all` shows it as done.
3. In a real session in a project, do a small piece of work, tell Claude a decision with its reason and a next step you don't want done yet, then type "hand off". Claude saves a labelled note and answers in one line.
4. Start a new session in the same project and ask, without letting it read files, what the next step is and why the decision went the way it did. Claude answers from the note.
5. Start a session in a different project and ask the same question. Claude has nothing.
6. `handoff done` in the first project; a new session there starts with no note.

## Notes for the builder

- Built and tested on macOS 27 with Python 3.14, git and Claude Code 2.1.321. A copy with a 500-character limit, a two-day age limit and startup-only display passed nineteen unit checks: each kind of refused note, the header fields, one note shared across folders of a git repository, the age limit, the startup filter, retiring, a body line starting "done:" that must not retire a note, and three notes saved in the same second. That last case came from reading the code before release: notes saved in the same second used to overwrite one another, and the check was added with the fix.
- Live testing used fresh headless sessions (`claude -p`, Sonnet) in a scratch git repository. The first created a file, was told that alpha won over beta because beta is deprecated upstream and that adding gamma could wait, and saved a note with State, Decided and Next. A new session in that repository answered both questions from the note without reading a file. A session in another repository answered NONE.
- The note is shown at every kind of session start by default, including after a compaction, where it backs up the compaction summary. Users who only want it on a fresh start set `SOURCES` to `('startup',)`.
- Claude decides what goes into a note, and an automatic compaction can arrive before anyone asks for one. Users who run long sessions can tell Claude in CLAUDE.md to offer a hand-off when a session has run long.
- Notes stay on the machine, in plain files the user can read, edit or delete.
