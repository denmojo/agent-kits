# Agent Kits

Build instructions for tools from my Claude Code setup, written so your own Claude can recreate them on your machine. Each kit is one markdown file. Hand it to Claude Code and say "build this."

## How a kit works

Every kit runs in two phases. In Phase 1, Claude looks at your machine (operating system, Python version, which folders exist, whether a port is free) and puts a table of choices in front of you, each with a default filled in. It writes nothing until you confirm or change them. Phase 2 builds with your answers and runs the tests.

The code in a kit is the code running on my machine with the personal details taken out. Each file carries its choices in a settings block at the top, so Phase 2 edits only that block. Where safety is in play, the default is the narrow choice, such as a page only your own machine can open.

Each kit says which platform it was tested on and what wasn't tested.

## Kits

| Kit | Builds |
| --- | --- |
| [Pasteboard](pasteboard.md) | A private web page where Claude Code replies are posted verbatim, rendered as markdown, with Board and Saved tabs, live updates, a `/pasteboard` skill and a Stop hook, plus a New form for pasting text from elsewhere that Claude reads back as data, never as instructions |
| [Vault Structure](vault-structure.md) | An Obsidian vault layout Claude Code follows, in a personal or a work profile: notes filed by type, Maps of Content by topic, an `AGENTS.md` rulebook loaded into every session, standing rules for anything that leaves the machine, and an optional backfill that links an adopted vault's old notes |
