# Recipe: Corrections Become Guards

To Claude, reading this for your user: this recipe runs in two phases. In Phase 1 you look at their setup, walk your user through the choices below and write nothing. In Phase 2 you build with their answers: copy each file exactly as given, change only the lines inside each script's Settings block, fill in the bracketed placeholders, show your user each file before you save it, and run the tests before you report it done.

## What it is

Most people correct Claude Code the same way they'd correct a colleague: they say it, and maybe ask Claude to remember it. The note goes into CLAUDE.md or a memory file. Three weeks later, deep in a long session, the same mistake comes back, because a note only works while the model reads it, weighs it and chooses to follow it.

Claude Code has a stronger tool for rules a program can check. A PreToolUse hook runs before every tool call and can refuse it, with a reason Claude reads. A guard built that way holds in every session, after every compaction, whatever the model happens to be paying attention to.

This kit makes that the habit. A skill tells Claude to sort each correction first. A rule a program can check (a command, a file, a string, a required step) becomes a guard, tested on both sides and logged. Only a rule that needs judgment (tone, taste, when to ask) goes into CLAUDE.md as a line in the user's words. Two working guards come with it, so most corrections need one new line in a list rather than new code: `guard-paths` refuses writes to protected files, and `guard-commands` refuses shell commands matching a pattern. Each block tells Claude why, in the words the user used when they made the rule.

## What it needs

- Claude Code, with hooks enabled (the default).
- Python 3.8 or newer, standard library only.

## Parts

| Part | Default location | Role |
| --- | --- | --- |
| `SKILL.md` | `~/.claude/skills/guard-it/` | Sorts a correction, picks the lightest guard that holds, tests it, records it |
| `guard-paths` | `~/.claude/guards/` | PreToolUse hook on Write, Edit and NotebookEdit; refuses protected paths |
| `guard-commands` | `~/.claude/guards/` | PreToolUse hook on Bash; refuses commands matching a pattern |
| `guards.md` | `~/.claude/guards.md` | The list of guards: each correction, what enforces it, how it was tested |
| `guards.log` | `~/.claude/guards.log` | One line per refused call |
| Hook entries | `~/.claude/settings.json` | Wire the two guards |

## Phase 1: look, then ask

Write nothing in this phase.

Look first: `python3 --version`; the `hooks.PreToolUse` and `permissions.deny` sections of `~/.claude/settings.json` and of the project's `.claude/settings.json`; the user's CLAUDE.md files, for rules already written as notes that a guard could enforce; and whether `~/.claude/skills/guard-it/` exists.

Then put this table in front of your user with the defaults filled in, and wait for their answers. Offer to list the CLAUDE.md rules you found that a guard could hold; converting them is a good first use of the skill once it is built.

| # | Choice | Default | Where the answer goes |
| --- | --- | --- | --- |
| 1 | Folder for the guard scripts | `~/.claude/guards` | Where both scripts go; `[GUARD DIR]` in the skill; the hook commands |
| 2 | Guard list file | `~/.claude/guards.md` | `[GUARD LIST]` in the skill |
| 3 | Skill name, which is also its slash command | `guard-it` | The skill's folder and `[COMMAND]` |
| 4 | Starting file rules | `.env` files and `~/.ssh/` | `PROTECTED` in `guard-paths` |
| 5 | Starting command rules | Force push, a download piped into a shell, deleting the home or root folder | `RULES` in `guard-commands` |
| 6 | Block log | `~/.claude/guards.log` | `LOG_FILE` in both scripts; `''` for none |
| 7 | Every project or one project | Every project | `~/.claude/settings.json` and `~/.claude/skills/`, or the project's `.claude/` |
| 8 | A line in CLAUDE.md pointing at the skill | Yes | Phase 2, step 5 |

## Phase 2: build

1. Create the folder from row 1. Save `guard-paths` and `guard-commands` there, edit only their Settings blocks to match rows 4 to 6, and run `chmod +x` on both.
2. Save the skill as `SKILL.md` in the skills folder for rows 3 and 7, replacing `[COMMAND]`, `[GUARD DIR]` and `[GUARD LIST]` everywhere.
3. Save `guards.md` at the row 2 path, with one row per starting rule.
4. Add the two PreToolUse entries to the settings file for row 7, merging into any existing `hooks.PreToolUse` array rather than replacing it.
5. If row 8 is yes, add this line to the user's CLAUDE.md: `When I correct you or set a standing rule, use the [COMMAND] skill before writing anything down.`
6. Start a new session so the hooks and the skill load, then run the tests and report each result.

## The skill: `SKILL.md`

````markdown
---
name: [COMMAND]
description: Use when the user corrects Claude Code or states a standing rule ("never do X", "always do Y first", "stop doing Z"), says "make that a rule" or "guard that", or runs /[COMMAND]. Decides whether the rule can be enforced by a hook or a settings rule instead of a memory note, builds and tests that guard, and records it.
---

# Turn corrections into guards

A memory note asks the model to remember. A guard makes the mistake impossible, in this session and every later one. When the user corrects you or sets a rule, sort it before writing anything down.

## 1. Sort the rule

- Mechanical: a program can check it with no judgment. A forbidden command or flag, a protected file or folder, a banned string in a commit message, a step that must come before an action. Build a guard.
- Judgment: applying it takes a model. Tone, design taste, when to ask a question. Write one line in CLAUDE.md, in the user's words, and stop there.
- High stakes: deleting, overwriting, pushing, publishing, sending, deploying. Build a guard even when the rule seems obvious, and make it block rather than warn.

One correction can hold both kinds. "Never force-push, and tell me why when you'd want to" is a guard for the first half and a CLAUDE.md line for the second.

## 2. Pick the lightest mechanism that holds

1. A permissions rule in settings.json, such as `"Bash(git push --force:*)"` or `"Edit(./secrets/**)"` under `permissions.deny`. No code. Claude only sees a bare refusal, with no reason attached.
2. A new row in an existing guard: `RULES` in `[GUARD DIR]/guard-commands` for a shell command, `PROTECTED` in `[GUARD DIR]/guard-paths` for a file. Use this when Claude should be told why.
3. A new hook script, when the check needs logic neither guard has: reading inside a commit message, checking a file's contents, requiring an earlier step. Copy guard-commands as the starting point: read the hook JSON on stdin, decide, print a deny with the reason, exit 0 on any error, and register it in settings.json under `hooks.PreToolUse` with a matcher for the tool it watches.

The reason text is the user's own words, shortened if needed. The next session reads it when it hits the guard.

## 3. Test before you report

Test both sides: one input that must be blocked, and one near miss that must pass.

```bash
[GUARD DIR]/guard-commands test 'git push -f origin main'      # must print the block
[GUARD DIR]/guard-commands test 'git push origin main'         # must print allowed
echo '{"tool_input":{"file_path":".env"},"cwd":"'"$PWD"'"}' | [GUARD DIR]/guard-paths   # the hook path itself
```

A pattern that also blocks the near miss is worse than none, because the user will switch it off. Tighten it until both tests come out right. A settings.json change shows in a new session; check it there.

## 4. Record it

Add a row to `[GUARD LIST]`: the date, the correction in the user's words, what enforces it, and the two test inputs. If a CLAUDE.md line or memory note already said the same thing, delete it, since the guard replaces it.

## 5. Tell the user in one line

Say what now enforces the rule and how it was tested. Skip promises about the future; the guard is the promise.

## When a guard blocks you

Read the reason, then take another route or ask the user. Never work around a guard with another command, another tool or a renamed file to get the same effect. If the guard is wrong, say so and propose a fix to the guard itself.
````

## The file guard: `guard-paths`

Settings block: `PROTECTED` (row 4), `LOG_FILE` (row 6).

````python
#!/usr/bin/env python3
"""guard-paths - a PreToolUse hook that stops Claude Code writing to protected files.

Runs before every Write, Edit and NotebookEdit call. When the target matches
a pattern in PROTECTED, the call is denied and Claude is told the reason, so
it can explain to the user instead of retrying. Every other call passes.

Patterns are shell-style (fnmatch) on the absolute path, where * also
crosses folder boundaries: '*/.env' matches a .env file anywhere.

  guard-paths            hook entry; reads the hook JSON on stdin
  guard-paths test PATH  print what the guard would decide for PATH

Standard library only. On any error the call passes: a broken guard must
never block every edit, so test it after each change.
"""
import datetime
import fnmatch
import json
import os
import sys

# ---- Settings ----------------------------------------------------------
PROTECTED = [                     # (pattern, reason Claude is given)
    ('*/.env', 'secrets file; ask the user to change it themselves'),
    ('*/.env.*', 'secrets file; ask the user to change it themselves'),
    (os.path.expanduser('~/.ssh/*'), 'SSH keys and config are never edited by Claude'),
]
LOG_FILE = os.path.expanduser('~/.claude/guards.log')   # one line per block; '' to keep no log
# ------------------------------------------------------------------------

NAME = 'guard-paths'


def decide(path, cwd=''):
    if not path:
        return None
    full = os.path.abspath(os.path.join(cwd or os.getcwd(), os.path.expanduser(path)))
    for pattern, reason in PROTECTED:
        if fnmatch.fnmatch(full, os.path.expanduser(pattern)):
            return f'{full} is protected ({reason}). Blocked by {NAME}.'
    return None


def log(line):
    if not LOG_FILE:
        return
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f'{datetime.datetime.now().isoformat(timespec="seconds")}\t{NAME}\t{line}\n')
    except OSError:
        pass


def main():
    if sys.argv[1:2] == ['test']:
        print(decide(sys.argv[2] if len(sys.argv) > 2 else '') or 'allowed')
        return
    h = json.loads(sys.stdin.read() or '{}')
    ti = h.get('tool_input') or {}
    reason = decide(ti.get('file_path') or ti.get('notebook_path') or '', h.get('cwd', ''))
    if reason:
        log(reason)
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                                                 'permissionDecision': 'deny',
                                                 'permissionDecisionReason': reason}}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
````

## The command guard: `guard-commands`

Settings block: `RULES` (row 5), `LOG_FILE` (row 6).

````python
#!/usr/bin/env python3
"""guard-commands - a PreToolUse hook that stops shell commands the user has ruled out.

Runs before every Bash call. When the command matches a regular expression
in RULES, the call is denied and Claude is told the reason, so it can take
another route or ask. Every other command passes.

  guard-commands              hook entry; reads the hook JSON on stdin
  guard-commands test 'CMD'   print what the guard would decide for CMD

A rule added after a correction carries the user's reason in their own
words, so the next session meets the same explanation they gave.

Standard library only. On any error the command passes: a broken guard must
never block every command, so test it after each change.
"""
import datetime
import json
import os
import re
import sys

# ---- Settings ----------------------------------------------------------
RULES = [                         # (regular expression, reason Claude is given)
    (r'\bgit\s+push\b[^;&|]*\s(--force|-f)(?=\s|$)', 'force pushes rewrite shared history; ask the user first'),
    (r'\bcurl\b[^|;&]*\|\s*(sudo\s+)?(ba|z)?sh\b', 'piping a download straight into a shell; download, read, then run'),
    (r'\brm\s+-[a-zA-Z]*r[a-zA-Z]*f?\s+(/|~|\$HOME)\s*($|;|&)', 'deleting a home or root folder'),
]
LOG_FILE = os.path.expanduser('~/.claude/guards.log')   # one line per block; '' to keep no log
# ------------------------------------------------------------------------

NAME = 'guard-commands'


def decide(cmd):
    for pattern, reason in RULES:
        if re.search(pattern, cmd or ''):
            return f'Command blocked by {NAME}: {reason}.'
    return None


def log(line):
    if not LOG_FILE:
        return
    try:
        with open(LOG_FILE, 'a') as f:
            f.write(f'{datetime.datetime.now().isoformat(timespec="seconds")}\t{NAME}\t{line}\n')
    except OSError:
        pass


def main():
    if sys.argv[1:2] == ['test']:
        print(decide(' '.join(sys.argv[2:])) or 'allowed')
        return
    h = json.loads(sys.stdin.read() or '{}')
    cmd = (h.get('tool_input') or {}).get('command', '')
    reason = decide(cmd)
    if reason:
        log(f'{reason}\t{cmd[:200]}')
        print(json.dumps({'hookSpecificOutput': {'hookEventName': 'PreToolUse',
                                                 'permissionDecision': 'deny',
                                                 'permissionDecisionReason': reason}}))


if __name__ == '__main__':
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
````

## The guard list: `guards.md`

````markdown
# Guards

Each row is a rule the user set and the program that now enforces it. Rules that need judgment live in CLAUDE.md instead.

| Date | Correction | Enforced by | Tests |
| --- | --- | --- | --- |
| [DATE] | Never touch .env files or ~/.ssh | PROTECTED in guard-paths | blocked: `.env`; allowed: `config.yaml` |
| [DATE] | No force pushes, no download piped into a shell, no deleting home or root | RULES in guard-commands | blocked: `git push -f origin main`; allowed: `git push origin main` |
````

## The hook entries

````json
{
  "hooks": {
    "PreToolUse": [
      { "matcher": "Write|Edit|NotebookEdit",
        "hooks": [ { "type": "command", "command": "$HOME/.claude/guards/guard-paths" } ] },
      { "matcher": "Bash",
        "hooks": [ { "type": "command", "command": "$HOME/.claude/guards/guard-commands" } ] }
    ]
  }
}
````

## Tests

Run these in order and report each result to the user.

1. `guard-commands test 'git push -f origin main'` prints the block; `guard-commands test 'git push --force-with-lease origin main'` prints `allowed`.
2. `guard-paths test ~/project/.env` prints the block; `guard-paths test ~/project/config.yaml` prints `allowed`.
3. In a new session, ask Claude to create a `.env` file. The write is refused, Claude says why, and it doesn't try another route.
4. Give Claude a correction a program can check, such as "never run npm publish yourself; I publish." Claude adds a rule to `guard-commands`, tests both sides, adds a row to the guard list, and answers in a line or two.
5. In a new session, ask Claude to run `npm publish`. The guard refuses it and Claude points the user at the rule.
6. Give Claude a judgment correction, such as "keep replies shorter." It goes into CLAUDE.md as one line, with no guard built.
7. `tail ~/.claude/guards.log` shows one line per refusal from tests 3 and 5.

## Notes for the builder

- Built and tested on macOS 27 with Python 3.14 and Claude Code 2.1.321. Copies with changed rules passed nineteen unit checks: relative paths resolved against the session folder, folder patterns, NotebookEdit, the near misses for each command rule, garbage input and the log. Testing caught one bad pattern before release: the force-push rule also blocked `--force-with-lease`, the safe variant, and now ends at a space or the end of the command.
- Live testing used fresh headless sessions (`claude -p`, Sonnet) with only this kit installed. Told "never run npm publish yourself", Claude added the rule, tested it both ways and wrote the row. A second session asked to publish was refused and declined to work around the guard; a third was refused a `.env` write, and no file appeared.
- That run also showed the limit of matching text. While logging its new rule, Claude's own `echo` mentioning "npm publish" was refused, because the guard sees the words, not their purpose. Keep command patterns anchored to the command itself, and expect the odd false refusal; the skill's near-miss test is there to keep them rare.
- `guard-paths` sees the Write, Edit and NotebookEdit tools only. A shell redirect such as `echo x > .env` goes through Bash, which is `guard-commands` territory. The skill forbids working around a guard, and the live run held to it, but a file that must never change deserves an operating-system permission as well.
- Rule 2 in the skill prefers a plain `permissions.deny` entry when no reason needs giving. It is a built-in Claude Code feature and needs no script.
