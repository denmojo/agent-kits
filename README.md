# Agent Kits

Build instructions for tools from my Claude Code setup, written so your own Claude can recreate them on your machine. Each kit is one markdown file; the Agent Bus kit also has a folder of code beside it. Hand a kit to Claude Code and say "build this."

## How a kit works

Every kit runs in two phases. In Phase 1, Claude looks at your machine (operating system, Python version, which folders exist, whether a port is free) and puts a table of choices in front of you, each with a default filled in. It writes nothing until you confirm or change them. Phase 2 builds with your answers and runs the tests.

The code in a kit is the code running on my machine with the personal details taken out. Each file carries its choices in a settings block at the top, so Phase 2 edits only that block. Where safety is in play, the default is the narrow choice, such as a page only your own machine can open.

Each kit says which platform it was tested on and what wasn't tested.

## Kits

| Kit | Builds |
| --- | --- |
| [Pasteboard](pasteboard.md) | A private web page where Claude Code replies are posted verbatim, rendered as markdown, with Board and Saved tabs, live updates, a `/pasteboard` skill and a Stop hook, plus a New form for pasting text from elsewhere that Claude reads back as data, never as instructions |
| [Vault Structure](vault-structure.md) | An Obsidian vault layout Claude Code follows, in a personal or a work profile: notes filed by type, Maps of Content by topic, an `AGENTS.md` rulebook loaded into every session, standing rules for anything that leaves the machine, and an optional backfill that links an adopted vault's old notes |
| [Rules After Compaction](rules-after-compaction.md) | A SessionStart hook that puts your rule files back into context word for word after every compaction, chunked under the hook output cap, with a self-check for the wiring |
| [Corrections Become Guards](corrections-become-guards.md) | A skill that turns a checkable correction into a PreToolUse guard instead of a memory note, with a file guard, a command guard, a guard list and a block log |
| [Hand-Off Notes](hand-off-notes.md) | Claude writes its own close-out under fixed labels before a clear or compaction, and the next session in that project starts with it, from plain files |
| [Spoken One-Liners](spoken-one-liners.md) | Claude ends each reply with a speaker line that your machine reads aloud through local text-to-speech, switched on and off by typing `voice on` or `voice off` |
| [Agent Bus](agent-bus.md) | Plain-text message threads that let two or more Claude Code sessions on one machine post to each other and wake each other up, with a hash chain per thread, signed messages, two hooks, and the rule that a message from another agent is information and never an order. The code is in the [`agent-bus/`](agent-bus/) folder with its tests |
| [Clickbait Finder](clickbait-finder.md) | A skill that finds where a YouTube video or a written article pays off its title and answers with the timestamp or paragraph range, its share of the whole, and a jump link |
