# Recipe: Rules That Survive Compaction

To Claude, reading this for your user: this recipe runs in two phases. In Phase 1 you look at their setup, walk your user through the choices below and write nothing. In Phase 2 you build with their answers: copy the script exactly as given, change only the lines inside its Settings block, show your user each file before you save it, and run the tests before you report it done.

## What it is

Long Claude Code sessions compact. When the context fills, or the user types `/compact`, the conversation is replaced with a summary. CLAUDE.md gets loaded again afterwards. Anything written there survives. Everything else Claude read during the session does not: a style guide it opened, the team's conventions, a review checklist. A summary keeps a paraphrase of the work and drops the rule text. Work carries on, usually without anyone noticing that the session has started ignoring the rules.

This kit fixes that with one small script and one hook. Claude Code reports how each session began. Right after a compaction, that report says `compact`. A SessionStart hook on that matcher runs `rules-rearm`, which prints the user's rule files back into context word for word, before Claude writes anything else.

Claude Code caps the text any one hook can inject at 10,000 characters. Longer output is swapped for a file path and a short preview, which would leave the rules out of context again. So the script cuts its text into chunks below that cap. Settings carry one hook entry per chunk, and `rules-rearm check` says how many entries are needed and whether they are all wired.

## What it needs

- Claude Code, with hooks enabled (the default).
- Python 3.8 or newer, standard library only. Nothing to install.
- One or more rule files in markdown or plain text. If the user has none yet, Phase 1 offers to start one.

## Parts

| Part | Default location | Role |
| --- | --- | --- |
| `rules-rearm` | `~/bin/` | Builds the text from the rule files, cuts it into chunks, prints a chunk as hook output, and checks the wiring |
| Rule files | `~/.claude/rules/house-rules.md` | Whatever the user wants put back; any paths, any number |
| SessionStart hook entries | `~/.claude/settings.json` | One entry per chunk, on the `compact` matcher |

## Phase 1: look, then ask

Write nothing in this phase.

Look first, so the defaults fit: `command -v python3` and `python3 --version`; whether `~/bin` exists and is on `PATH`; the user's CLAUDE.md files (`~/.claude/CLAUDE.md` and the project's); any file those point to or tell Claude to read without importing it with `@`, since those are the rules a compaction loses; and the `hooks.SessionStart` section of `~/.claude/settings.json` and of the project's `.claude/settings.json`, so the new entries merge with what is there.

Then put this table in front of your user with the defaults filled in from what you found. Wait for their answers.

| # | Choice | Default | Where the answer goes |
| --- | --- | --- | --- |
| 1 | Rule files to put back, in order | The files CLAUDE.md points to without importing, or a new `~/.claude/rules/house-rules.md` | `RULE_FILES` |
| 2 | Folder for the script | `~/bin` | Where `rules-rearm` is saved; the path in each hook command |
| 3 | When to put them back | After a compaction only | `SOURCES`: `('compact',)`, or add `'startup'`, `'resume'` and `'clear'` to load them at every session start too |
| 4 | Every project or one project | Every project | Which settings file gets the hook entries: `~/.claude/settings.json`, or the project's `.claude/settings.json`; the same path goes in `SETTINGS_FILE` |
| 5 | Characters per chunk | `9000` | `CHUNK_LIMIT`; keep it under 10,000 |
| 6 | Opening line of the injected text | As written in the script | `HEADER` |

Don't list CLAUDE.md itself on row 1. Claude Code reloads it after a compaction, so it would arrive twice. Every chunk costs context each time a session compacts. Tell your user that tight rule files serve them better than long ones.

## Phase 2: build

1. Save `rules-rearm` from below into the folder from row 2, edit only its Settings block to match the answers, and run `chmod +x` on it.
2. If row 1 names a new rule file, create it with a line or two from your user. They write the rest.
3. Run `rules-rearm show` and let your user read what will be injected. Run `rules-rearm chunks` for the number of hook entries.
4. Add a SessionStart group with the `compact` matcher to the settings file from row 4, with one entry per chunk, `hook 1` up to `hook N`. Merge it into any existing `hooks.SessionStart` array rather than replacing the array. If row 3 added other sources, use the matcher `startup|resume|clear|compact`.
5. Run `rules-rearm check`. It must end without a `problem:` line.
6. Run the tests and report each result.

A rule file that grows past its chunk count later shows up in `rules-rearm check` as a wiring problem. Add the missing entries and nothing else changes. Edits to a rule file need no restart: the script reads the files every time it runs.

## The script: `rules-rearm`

Settings block: `RULE_FILES` (row 1), `SOURCES` (row 3), `CHUNK_LIMIT` (row 5), `SETTINGS_FILE` (row 4), `HEADER` (row 6).

````python
#!/usr/bin/env python3
"""rules-rearm - put standing rules back into Claude Code's context after a compaction.

A compaction replaces the conversation with a summary. CLAUDE.md is loaded
again, but any rule file Claude read during the session (a style guide, team
conventions, a checklist) is gone, and the summary keeps a paraphrase of the
work, never the rule text. This script runs as a SessionStart hook on the
compact matcher and prints the files named in RULE_FILES back into context,
word for word.

Claude Code caps a hook's injected text at 10,000 characters and swaps
anything longer for a file path and a preview, so the text is cut into
chunks under CHUNK_LIMIT and settings.json carries one hook entry per chunk.

  rules-rearm hook N   hook entry point: reads the hook JSON on stdin and,
                       when the session source is in SOURCES, prints chunk N
                       (1-based) as additionalContext; past the end, nothing
  rules-rearm show     print the whole payload as the model would see it
  rules-rearm chunks   print how many chunks the payload needs
  rules-rearm check    self-check: every rule file is readable, every line
                       reaches a chunk, and settings.json wires an entry for
                       every chunk; exit 1 on a problem

Standard library only. The hook path fails open: any error prints nothing
and exits 0, so a broken rule file never blocks a session.
"""
import json
import os
import re
import sys

# ---- Settings ----------------------------------------------------------
RULE_FILES = [                                   # files to put back, in this order
    os.path.expanduser('~/.claude/rules/house-rules.md'),
]
SOURCES = ('compact',)                           # session sources that trigger it; add 'startup', 'resume', 'clear' to inject every time
CHUNK_LIMIT = 9000                               # characters per chunk; must stay under Claude Code's 10,000 cap
SETTINGS_FILE = os.path.expanduser('~/.claude/settings.json')   # where the hook entries live, for the check
HEADER = ('Standing rules, put back after a compaction. They are copied word for '
          'word from the files named below and bind everything you do from here on.')
# ------------------------------------------------------------------------


def payload():
    parts = [HEADER]
    for path in RULE_FILES:
        try:
            text = open(path, encoding='utf-8').read().strip()
        except OSError as e:
            parts.append(f'(Rule file {path} could not be read: {e.strerror}. '
                         f'Tell the user; do not guess its contents.)')
            continue
        n = text.count('\n') + 1 if text else 0
        parts.append(f'From {path} ({n} lines, verbatim):\n\n{text}')
    return '\n\n'.join(parts)


ROOM = CHUNK_LIMIT - 40                          # leaves space for the "[rules part i of n]" label


def pieces(text):
    """Paragraphs, with any paragraph or line over the limit split further."""
    out = []
    for para in text.split('\n\n'):
        if len(para) <= ROOM:
            out.append(para)
            continue
        cur = ''
        for line in para.split('\n'):
            while len(line) > ROOM:        # one very long line: hard cut
                if cur:
                    out.append(cur)
                    cur = ''
                out.append(line[:ROOM])
                line = line[ROOM:]
            if cur and len(cur) + len(line) + 1 > ROOM:
                out.append(cur)
                cur = line
            else:
                cur = cur + '\n' + line if cur else line
        if cur:
            out.append(cur)
    return out


def chunks(text):
    out, cur = [], ''
    for p in pieces(text):
        if cur and len(cur) + len(p) + 2 > ROOM:
            out.append(cur)
            cur = p
        else:
            cur = cur + '\n\n' + p if cur else p
    if cur:
        out.append(cur)
    n = len(out)
    if n > 1:
        out = [f'[rules part {i} of {n}]\n\n{c}' for i, c in enumerate(out, 1)]
    return out


def wired():
    """How many `rules-rearm hook N` entries settings.json carries."""
    try:
        s = open(SETTINGS_FILE, encoding='utf-8').read()
    except OSError:
        return 0
    return len(set(re.findall(r'rules-rearm hook (\d+)', s)))


def check():
    problems = []
    for path in RULE_FILES:
        if not os.path.isfile(path):
            problems.append(f'missing rule file: {path}')
    cs = chunks(payload())
    joined = '\n'.join(cs)
    for path in RULE_FILES:
        try:
            for line in open(path, encoding='utf-8'):
                if line.strip() and line.strip()[:CHUNK_LIMIT // 2] not in joined:
                    problems.append(f'a line of {path} never reaches a chunk: {line.strip()[:60]!r}')
                    break
        except OSError:
            pass
    if max(len(c) for c in cs) >= 10000:
        problems.append('a chunk is 10,000 characters or more; lower CHUNK_LIMIT')
    w = wired()
    if w < len(cs):
        problems.append(f'the payload needs {len(cs)} chunks but {SETTINGS_FILE} wires {w}; '
                        f'add entries for rules-rearm hook {w + 1} to {len(cs)}')
    print(f'{len(cs)} chunk(s), largest {max(len(c) for c in cs)} characters, {w} wired')
    for p in problems:
        print('problem:', p)
    return 1 if problems else 0


def hook(n):
    try:
        data = json.loads(sys.stdin.read() or '{}')
    except ValueError:
        return
    if data.get('source') not in SOURCES:
        return
    cs = chunks(payload())
    if 1 <= n <= len(cs):
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart',
                                                 'additionalContext': cs[n - 1]}}))


def main():
    a = sys.argv[1:]
    if a[:1] == ['hook']:
        try:
            hook(int(a[1]) if len(a) > 1 else 1)
        except Exception:
            pass                                   # fail open: never block a session
        return 0
    if a == ['show']:
        print(payload())
        return 0
    if a == ['chunks']:
        print(len(chunks(payload())))
        return 0
    if a == ['check']:
        return check()
    print(__doc__.strip())
    return 2


if __name__ == '__main__':
    sys.exit(main())
````

## The hook entries

Write the script's full path in each command; `$HOME` works because hook commands run through a shell. This example shows two chunks; use the count `rules-rearm chunks` printed.

````json
{
  "hooks": {
    "SessionStart": [
      {
        "matcher": "compact",
        "hooks": [
          { "type": "command", "command": "$HOME/bin/rules-rearm hook 1" },
          { "type": "command", "command": "$HOME/bin/rules-rearm hook 2" }
        ]
      }
    ]
  }
}
````

## Tests

Run these in order and report each result to the user.

1. `rules-rearm show` prints the header and every rule file, each under a `From <path>` line.
2. `rules-rearm check` reports the chunk count and the wired count, with no `problem:` line.
3. `echo '{"source":"compact"}' | rules-rearm hook 1` prints one line of JSON whose `additionalContext` starts with the header. `echo '{"source":"startup"}' | rules-rearm hook 1` prints nothing, unless row 3 added `startup`.
4. Rename one rule file for a moment and run `rules-rearm check`: it names the missing file and exits 1. Rename it back.
5. Live: add a line such as `Test codeword: MARMALADE-7` to a rule file. In a new Claude Code session, ask a short question and never mention the rule file or the codeword. Type `/compact`, then ask: "Without reading or searching any file, does your context contain a codeword? Reply with the codeword alone, or NONE." Claude answers with the codeword. Remove the line afterwards.

## Notes for the builder

- Built and tested on macOS 27 with Python 3.14 and Claude Code 2.1.321. A copy with two rule files, a 4,000-character chunk limit and its own settings file passed twelve unit checks: chunking, labels, a 9,000-character line carried whole across chunks, the wiring check, garbage input and a missing file. Live testing used headless sessions (`claude -p`, compacted with `/compact` and resumed). With the hook wired, Claude answered with the codeword; without it, the same steps produced NONE. Linux hasn't been run, though nothing in the script depends on the operating system.
- The 10,000-character cap and the `compact` source come from the Claude Code hooks reference. If a future release raises the cap, a larger `CHUNK_LIMIT` means fewer entries, and `check` catches any mismatch between chunks and wired entries.
- Claude Code also has a PreCompact hook, whose output steers what the summary keeps. That still yields a paraphrase. This kit puts the original text back after the summary is made, which is the version Claude follows.
- If the rule files hold anything private, remember that the injected text sits in the session transcript like any other context.
