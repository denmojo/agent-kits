# Recipe: Spoken One-Liners for Claude Code

To Claude, reading this for your user: this recipe runs in two phases. In Phase 1 you look at their machine, walk your user through the choices below and write nothing. In Phase 2 you build with their answers: copy the script exactly as given, change only the lines inside its Settings block, show your user each file before you save it, and run the tests before you report it done.

## What it is

Claude Code works quietly. A long turn can end while the user is in another window, and the first sign of it is a cursor sitting idle. This kit gives each reply a voice: Claude ends the reply with one line that starts with a speaker glyph (🔊), and the computer reads that line aloud the moment the turn ends. The user hears "renamed the three config files and the tests pass" from across the room and knows whether to come back.

It runs on three hooks and one script, `say-line`. A Stop hook finds the speaker line in the turn that just ended and hands it to the machine's text-to-speech, in the background, so the session never waits on audio. A UserPromptSubmit hook watches for the prompts `voice on` and `voice off` and flips a switch file, so turning the voice on or off never depends on the model remembering an instruction. While the switch is on, a SessionStart hook reminds Claude to write the spoken line after any restart, clear or compaction.

If a reply comes without the speaker line, the script falls back to the last sentence of the reply. A new line cuts off one still playing, so replies never pile up into a queue of speech.

## What it needs

- Claude Code, with hooks enabled (the default).
- Python 3.8 or newer, standard library only.
- A text-to-speech command: `say` comes with macOS; on Linux, `spd-say` (speech-dispatcher) or `espeak-ng`.
- Speakers or headphones on the machine running Claude Code. Over SSH, the sound plays on the remote machine.

## Parts

| Part | Default location | Role |
| --- | --- | --- |
| `say-line` | `~/bin/` | The switch, the speaker, and all three hook entry points |
| Switch file | `~/.claude/say-line.state` | Holds `on` or `off` |
| Hook entries | `~/.claude/settings.json` | Stop, SessionStart and UserPromptSubmit, each running `say-line` |

## Phase 1: look, then ask

Write nothing in this phase.

Look first: `command -v python3` and `python3 --version`; whether `~/bin` exists and is on `PATH`; which speech command exists (`command -v say spd-say espeak-ng espeak`); on macOS, the voices installed (`say -v '?'`), and on Linux, `espeak-ng --voices`; and the `hooks` section of `~/.claude/settings.json`, so the new entries merge with what is there. Speak one test line with the engine you found, so your user hears what the default sounds like.

Then put this table in front of your user with the defaults filled in from what you found, and wait for their answers.

| # | Choice | Default | Where the answer goes |
| --- | --- | --- | --- |
| 1 | Folder for the script | `~/bin` | Where `say-line` is saved; the path in each hook command |
| 2 | Speech engine | `auto` (the first of `say`, `spd-say`, `espeak-ng`, `espeak` found) | `ENGINE` |
| 3 | Voice | The system default | `VOICE`, a name from the voice list |
| 4 | Speed, in words per minute | `190` | `RATE` (`spd-say` ignores it) |
| 5 | What the spoken line should sound like | One short, plain sentence saying what was just done | `STYLE`; some users prefer jokes, a character voice, or a status word |
| 6 | Prompts that switch the voice | `voice on` and `voice off` | `ON_PHRASE` and `OFF_PHRASE` |
| 7 | Speak the last sentence when a reply has no speaker line | Yes | `FALLBACK` |
| 8 | Every project or one project | Every project | `~/.claude/settings.json`, or the project's `.claude/settings.json` |

## Phase 2: build

1. Save `say-line` from below into the folder from row 1, edit only its Settings block to match the answers, and run `chmod +x` on it.
2. Add the three hook entries below to the settings file from row 8, merging into any existing `Stop`, `SessionStart` and `UserPromptSubmit` arrays rather than replacing them.
3. Run `say-line on`, then `say-line say "testing one two"`, and confirm your user heard it. Run `say-line off`.
4. Run the tests and report each result.

## The script: `say-line`

Settings block: `STATE_FILE`, `MARKER`, `ENGINE` (row 2), `VOICE` (row 3), `RATE` (row 4), `FALLBACK` (row 7), `MAXLEN`, `ON_PHRASE` and `OFF_PHRASE` (row 6), `STYLE` (row 5).

````python
#!/usr/bin/env python3
"""say-line - Claude Code speaks a one-line summary of each reply out loud.

While the voice is on, Claude ends every reply with a line that starts with
the speaker glyph (MARKER), and a Stop hook reads that line aloud through the
machine's text-to-speech. Typing the ON_PHRASE or OFF_PHRASE as a whole prompt
flips the switch through a UserPromptSubmit hook, so it never depends on the
model remembering. A SessionStart hook repeats the instruction after a clear,
a compaction or a restart while the voice is on.

  say-line on | off | status     flip or show the switch
  say-line say TEXT              speak TEXT now (if the switch is on)
  say-line stop-hook             Stop hook entry; reads the hook JSON on stdin
  say-line session-hook          SessionStart hook entry
  say-line prompt-hook           UserPromptSubmit hook entry
  say-line extract TRANSCRIPT    print the line it would speak for the last turn

SAYLINE_DRYRUN=FILE in the environment appends the speech command to FILE
instead of running it (for tests). Every hook path fails silent: an error
means no speech, never a blocked session. Standard library only.
"""
import json
import os
import re
import shutil
import signal
import subprocess
import sys
import time

# ---- Settings ----------------------------------------------------------
STATE_FILE = os.path.expanduser('~/.claude/say-line.state')   # holds 'on' or 'off'
MARKER = '\U0001F50A'          # the speaker glyph that starts the line to speak
ENGINE = 'auto'                # 'auto', 'say' (macOS), 'spd-say', 'espeak-ng' or 'espeak'
VOICE = ''                     # engine voice name; '' for the system default
RATE = 190                     # words per minute (say and espeak; spd-say ignores it)
FALLBACK = True                # with no marker line, speak the reply's last sentence instead
MAXLEN = 220                   # longest line spoken, in characters
ON_PHRASE = 'voice on'         # a prompt that is exactly this turns the voice on
OFF_PHRASE = 'voice off'       # ...and this turns it off
STYLE = 'one short, plain sentence saying what you just did'   # what the spoken line should sound like
# ------------------------------------------------------------------------

PID_FILE = STATE_FILE + '.pid'


def is_on():
    try:
        return open(STATE_FILE).read().strip() == 'on'
    except OSError:
        return False


def set_state(v):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, 'w') as f:
        f.write(v + '\n')


def instruction():
    return (f'Voice is on. End every reply with one final line that starts with the '
            f'{MARKER} glyph, followed by {STYLE}. That line is read aloud, so no code, '
            f'paths, markdown or URLs in it.')


def engine_cmd(text):
    eng = ENGINE
    if eng == 'auto':
        eng = next((e for e in ('say', 'spd-say', 'espeak-ng', 'espeak') if shutil.which(e)), '')
    if eng == 'say':
        return ['say'] + (['-v', VOICE] if VOICE else []) + ['-r', str(RATE), text]
    if eng == 'spd-say':
        return ['spd-say', '--wait'] + (['-y', VOICE] if VOICE else []) + [text]
    if eng in ('espeak-ng', 'espeak'):
        return [eng] + (['-v', VOICE] if VOICE else []) + ['-s', str(RATE), text]
    return None


def speak(text):
    if not is_on() or not text:
        return
    cmd = engine_cmd(text)
    if not cmd:
        return
    dry = os.environ.get('SAYLINE_DRYRUN')
    if dry:
        with open(dry, 'a') as f:
            f.write(json.dumps(cmd) + '\n')
        return
    try:                                # the newest line wins: stop one still playing
        old = int(open(PID_FILE).read())
        os.killpg(old, signal.SIGTERM)
    except (OSError, ValueError):
        pass
    p = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                         start_new_session=True)
    try:
        open(PID_FILE, 'w').write(str(p.pid))
    except OSError:
        pass
    p.wait()


def clean(s):
    s = re.sub(r'^\s*([-*+]\s+|\d+[.)]\s+|>\s+|#{1,6}\s+)', '', s)
    s = re.sub(r'\[([^\]]+)\]\([^)]*\)', r'\1', s)
    s = re.sub(r'(\*\*|__|~~|\*|`)', '', s)
    s = s.replace(MARKER, '')
    return re.sub(r'\s+', ' ', s).strip()


def extract(path):
    """The line to speak for the last turn: its marker line, else (FALLBACK) the
    last sentence of its final text. '' when the turn has no text yet."""
    return extract_info(path)[0]


def extract_info(path):
    """(line, from_marker) for the last turn."""
    last_prompt, texts, i = -1, {}, 0
    try:
        for raw in open(path, encoding='utf-8'):
            try:
                e = json.loads(raw)
            except ValueError:
                continue
            if e.get('isSidechain'):
                continue
            c = e.get('message', {}).get('content')
            if e.get('type') == 'user':
                if (isinstance(c, str) and c.strip()) or (isinstance(c, list) and any(
                        isinstance(b, dict) and b.get('type') == 'text' and b.get('text', '').strip() for b in c)):
                    last_prompt = i
            elif e.get('type') == 'assistant' and isinstance(c, list):
                t = '\n'.join(b.get('text', '') for b in c if isinstance(b, dict) and b.get('type') == 'text')
                if t.strip():
                    texts[i] = t
            i += 1
    except OSError:
        return '', False
    turn = [texts[k] for k in sorted(texts) if k > last_prompt]
    if not turn:
        return '', False
    for t in reversed(turn):
        marks = [ln.strip() for ln in t.splitlines() if ln.strip().startswith(MARKER)]
        if marks:
            return clean(marks[-1])[:MAXLEN], True
    if not FALLBACK:
        return '', False
    line, fence = '', False
    for ln in turn[-1].splitlines():
        st = ln.strip()
        if st.startswith('```'):
            fence = not fence
            continue
        if fence or not st or re.fullmatch(r'[-*_|: ]{3,}', st):
            continue
        c = clean(st)
        if c and not (' ' not in c and ('/' in c or c.startswith('http'))):
            line = c
    sentences = [s for s in re.split(r'(?<=[.!?])\s+', line) if s.strip()]
    out = sentences[-1] if sentences else line
    if len(out) > MAXLEN:
        out = out[:MAXLEN].rsplit(' ', 1)[0]
    return out, False


def speak_later(path):
    """Detached from the hook. The final message can reach the transcript a
    moment after Stop fires, so wait for a marker line, then for any text."""
    for wait_for_marker in (True, False):
        for _ in range(10 if wait_for_marker else 15):
            line, marked = extract_info(path)
            if line and (marked or not wait_for_marker):
                speak(line)
                return
            time.sleep(0.1)


def hook_input():
    try:
        return json.loads(sys.stdin.read() or '{}')
    except ValueError:
        return {}


def main():
    a = sys.argv[1:]
    cmd = a[0] if a else 'status'
    if cmd in ('on', 'off'):
        set_state(cmd)
        print(f'say-line: {cmd}')
    elif cmd == 'status':
        print('say-line:', 'on' if is_on() else 'off')
    elif cmd == 'say':
        speak(' '.join(a[1:]))
    elif cmd == 'extract' and len(a) > 1:
        print(extract(a[1]))
    elif cmd == 'stop-hook':
        h = hook_input()
        path = h.get('transcript_path', '')
        if is_on() and path:
            subprocess.Popen([sys.executable, os.path.abspath(__file__), '_later', path],
                             stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
                             stderr=subprocess.DEVNULL, start_new_session=True)
    elif cmd == '_later' and len(a) > 1:
        speak_later(a[1])
    elif cmd == 'session-hook':
        hook_input()
        if is_on():
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'SessionStart',
                                                     'additionalContext': instruction()}}))
    elif cmd == 'prompt-hook':
        p = ' '.join(str(hook_input().get('prompt', '')).split()).lower().rstrip('.!')
        if p == ON_PHRASE.lower():
            set_state('on')
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit',
                                                     'additionalContext': 'The user just turned the voice on. '
                                                     + instruction() + ' Acknowledge in one line.'}}))
        elif p == OFF_PHRASE.lower():
            set_state('off')
            print(json.dumps({'hookSpecificOutput': {'hookEventName': 'UserPromptSubmit',
                                                     'additionalContext': 'The user just turned the voice off. '
                                                     'Stop adding the spoken line. Acknowledge in one line.'}}))
    else:
        print(__doc__.strip())
        return 2
    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception:
        sys.exit(0)
````

## The hook entries

Use the full path from row 1; `$HOME` works because hook commands run through a shell.

````json
{
  "hooks": {
    "Stop": [
      { "hooks": [ { "type": "command", "command": "$HOME/bin/say-line stop-hook" } ] }
    ],
    "SessionStart": [
      { "matcher": "startup|resume|clear|compact",
        "hooks": [ { "type": "command", "command": "$HOME/bin/say-line session-hook" } ] }
    ],
    "UserPromptSubmit": [
      { "hooks": [ { "type": "command", "command": "$HOME/bin/say-line prompt-hook" } ] }
    ]
  }
}
````

## Tests

Run these in order and report each result to the user.

1. `say-line status` prints `say-line: off`.
2. In a new Claude Code session, type the row 6 on-phrase as the whole prompt. Claude acknowledges in one line ending with a 🔊 line, and your user hears that line. `say-line status` now prints `on`.
3. Ask a short question. The reply ends with a 🔊 line written in the row 5 style, and your user hears it within a second or two of the reply finishing.
4. Ask something that takes a few tool calls. Only the final line is spoken, once.
5. Type `/clear`, then ask another question. The spoken line is still there, because the SessionStart hook repeated the instruction.
6. Type the off-phrase. Claude acknowledges; the next reply has no 🔊 line and nothing is spoken.
7. Without speakers: `SAYLINE_DRYRUN=/tmp/said.log say-line on`, then `SAYLINE_DRYRUN=/tmp/said.log say-line say hello` writes the speech command to `/tmp/said.log` instead of playing it. Run `say-line off` afterwards.

## Notes for the builder

- Built and tested on macOS 27 with Python 3.14, Claude Code 2.1.321 and `say`. A copy with every setting changed (`espeak-ng` as the engine, a named voice, another rate, other switch phrases and style) passed fifteen unit checks with speech logged instead of played: the switch both ways, the session reminder, the line chosen from a marker or the fallback, markdown stripped, a speaker line from an earlier turn ignored, the background speaking, and garbage input. A live run in headless sessions (`claude -p`) typed `voice on`, asked a question, typed `voice off` and asked again: both replies while on ended with a speaker line that reached the speech command, and the reply after `voice off` had none and spoke nothing. The `spd-say` and `espeak-ng` command forms follow those tools' documented flags and haven't been run on Linux.
- The Stop hook returns at once and leaves a detached process to wait for the reply's last message, which can reach the transcript a moment after the turn ends. That process waits up to a second for a speaker line, then up to a second and a half more for any text.
- The switch phrase has to be the whole prompt (case, extra spaces and a trailing `.` or `!` ignored), so "voice on the bug report" never flips it.
- Spoken text stays on the machine: `say`, `spd-say` and `espeak-ng` all synthesize locally.
