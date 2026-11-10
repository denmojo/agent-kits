# Recipe: An Obsidian Vault Claude Code Can Keep

To Claude, reading this for your user: this recipe runs in two phases. In Phase 1 you look at their vault (or the folder that will become one), walk your user through the choices below and write nothing. In Phase 2 you build with their answers: create the folders, write each file from the templates here, fill in the bracketed placeholders, delete the template lines for parts they left out, show your user each file before you save it, and run the tests before you report it done.

## What it is

Notes pile up faster than anyone can file them. Left to itself, Claude Code drops a new note wherever the conversation happened to be, links it to whatever it remembers, and makes up a slightly different heading layout each time. After a few hundred notes nothing can be found by browsing, and the graph is a hairball.

This recipe gives the vault a layout Claude can follow without being told twice. Folders sort notes by what they are (a book summary, a meeting, a decision). Maps of Content (MOCs) sort the same notes by what they are about. The two never compete: a note lives in one folder and links up to one or two MOCs. An `AGENTS.md` at the vault root spells out every rule, and a two-line `CLAUDE.md` imports it so each session starts with the rules loaded.

It comes in two profiles. The personal profile files reading, research and reference notes under `Resources/` by type. The work profile files meetings, people, workstreams, decisions and weekly status, and adds rules for connectors that can send mail or post as the user. Either one can adopt an existing vault without moving a note, and can then link the old notes into the new structure after the user approves a plan.

Nothing here runs in the background. It is folders, templates and a rulebook, so it works the same with [Obsidian](https://obsidian.md/) open or closed, and with any sync method.

## What it needs

- Claude Code, run from the vault root.
- A markdown reader for the user: [Obsidian](https://obsidian.md/), [VS Code](https://code.visualstudio.com/) with the [Foam](https://marketplace.visualstudio.com/items?itemName=foam.foam-vscode) extension (`foam.foam-vscode`) so its wikilinks resolve, or any other reader they prefer. Claude only needs the folder.
- An existing vault to adopt, or an empty folder for a new one.
- Optional: git, which gives the user an undo for everything Claude writes.

## Parts

| Part | Location | Role |
| --- | --- | --- |
| `AGENTS.md` | Vault root | The rulebook: layout, MOC rules, note conventions, standing rules |
| `CLAUDE.md` | Vault root | Imports `AGENTS.md` into every session |
| Type folders | `Resources/` (personal) or the vault root (work) | Notes sorted by what they are |
| `MOC - [Theme].md` | `Resources/` (personal) or `MOCs/` (work) | One index per theme |
| Templates | `Templates/` folder of the profile | Skeletons Claude copies for new notes |
| `Home.md` | Vault root, optional | One entry point linking the MOCs and the most used notes |
| Optional top-level folders | Vault root | Drafts, design docs, ideas, prompts and the rest, as chosen |
| Read deny rule | `.claude/settings.json` in the vault | Keeps Claude out of `.obsidian/` |
| Git repository | The vault, optional | Undo for every change Claude makes |

## Phase 1: look, then ask

Write nothing in this phase.

Look at the folder first, so the defaults you offer fit it:

- whether it exists, and whether it holds `.obsidian/` (an existing vault);
- how many markdown files it has, and which top-level folders;
- whether `AGENTS.md`, `CLAUDE.md`, `Home.md` or `.claude/settings.json` already exist, and what they say;
- which folders hold which kinds of note, from a handful of notes read out of the biggest folders;
- whether the notes look like reading and reference (personal) or meetings and projects (work);
- whether the folder sits inside a cloud-synced path (iCloud Drive, OneDrive, Dropbox, Google Drive, or a path under `Library/CloudStorage` or `Library/Mobile Documents`);
- whether `git` is installed, and whether the folder is already a repository;
- which connectors and MCP tools this session has, and which of them can send, post or edit something outside the machine. Test nothing that writes.

Then put this table in front of your user with the defaults filled in from what you found, and ask them to confirm each row or change it.

| # | Choice | Default | Where the answer goes |
| --- | --- | --- | --- |
| 1 | Vault folder | The current folder if it holds `.obsidian/`, else ask | Where everything below is created |
| 2 | Profile: personal or work | Whichever the notes look like; personal for an empty folder | Which layout block, templates and MOC folder to use |
| 3 | New vault, or adopt an existing one | Adopt, if row 1 holds notes | In adopt mode no existing note moves; `AGENTS.md` maps existing folders to note types, and only missing types get new folders |
| 4 | Link the existing notes into the new structure (adopt only) | Yes | The backfill plan below, then Phase 2 step 9 |
| 5 | Owner's name and what the vault is for | Ask; one line | `[OWNER]` and `[PURPOSE]` in `AGENTS.md` |
| 6 | Note types | Personal: Books, Briefs, Personal, Technical, Field Guides, References. Work: Inbox, Meetings, People, Workstreams, Decisions, Briefs, Status, Daily | One folder each; the layout block in `AGENTS.md` |
| 7 | Optional extra note types | Personal: People, Video_Summaries, Podcasts. Work: none | Same as row 6 |
| 8 | Starting MOC themes | Three to six themes drawn from the notes read above; none for an empty vault | One MOC file each |
| 9 | Optional top-level folders | Drafts, Designs, Ideas, Prompts, Mail_Drop: yes. Infra, Library, Jots, Travel, Projects: no | Folders created; matching lines kept in `AGENTS.md`, the rest deleted |
| 10 | MOCs per note | At most two | `[CAP]` in `AGENTS.md` |
| 11 | Frontmatter fields on a note | `Date Added`, `Topic`; for any added field, ask what values it takes | `[FIELDS]` in `AGENTS.md`, with the allowed values of any added field after it; the templates. `[TEMPLATE RULE]` reads "`Resources/Templates/Resource Template.md` for every type" in the personal profile, and "the template in `Templates/` named for its type (Meeting, Person, Workstream, Decision, Weekly Status, Daily)" in the work profile |
| 12 | Type tag on a note's last line (such as `#books`) | Yes | The Tags paragraph of `AGENTS.md`, or deleted |
| 13 | Standing rules for anything that leaves the machine | Yes | The Standing rules section of `AGENTS.md` |
| 14 | Weekly status: who it goes to, on which day, for which meeting (work only) | Ask | `[STATUS AUDIENCE]` in `AGENTS.md` and the Weekly Status template |
| 15 | A `Home.md` entry point | Yes for work, no for personal | `Home.md` and its paragraph in `AGENTS.md` |
| 16 | Put the vault under git | Yes when git is installed and the folder isn't a repository yet | Phase 2 steps 1 and 10 |
| 17 | Keep Claude out of `.obsidian/` with a deny rule | Yes | `.claude/settings.json` in the vault |

Tell your user plainly about three of these:

- Row 3: adopt mode moves nothing. Moving old notes into the new type folders is a separate job, a folder at a time, done inside Obsidian, which rewrites links on a move. A move made in the shell or by Claude breaks them.
- Row 8: an MOC earns its place once a theme has about five notes the user goes back to. Suggest fewer themes rather than more; splitting a big MOC later is easy, merging thin ones is tedious.
- Row 16: if the vault sits in a cloud-synced folder, git and the sync service will both watch the same files. That works, but a `.git` folder inside iCloud Drive or OneDrive can sync slowly or conflict; say so, and let the user decide.

### The backfill plan (row 4 yes)

Once the table is settled, and still writing nothing, list every existing note with:

- a one-line description, read from the note itself;
- the note type it would have under the new layout (it stays where it is);
- its proposed MOC, or two at most, or "none" for a note that doesn't fit a theme yet;
- any direct link to another note you would add, each with the one sentence that explains it.

A vault with more than about 150 notes gets this plan a folder at a time. Show the plan and wait for the user's go before Phase 2.

## Phase 2: build

1. If row 16 is yes, run `git init` in the vault, write a `.gitignore` holding `.obsidian/workspace*.json` and `.trash/`, and commit everything as it stands, so the user can see and undo every change that follows.
2. Create the folders from rows 6, 7 and 9, and the MOC folder for the profile. Skip any that already exist.
3. Write the templates for the profile from the templates below, with the row 11 fields; the MOC template keeps `Date Added` and `Topic` only. Drop any template whose folder the user left out.
4. Write one MOC per row 8 theme from the MOC template, with today's date from the `date` command and a one-line Topic. Its opening paragraph says what the theme covers and what it leaves out. Name two or three sections after the notes it will hold, or leave one empty section for a new MOC.
5. Write `AGENTS.md` from the template below. Use the layout block for the profile and delete the other. Fill in every bracketed placeholder and keep only the lines for folders and parts the user chose. In adopt mode, add the vault's own folders to the layout block, each tagged with the note type its notes share; a folder of mixed notes goes in as existing notes not yet sorted, with a sentence under the block saying new notes go to the type folders and nothing in it moves unless the user asks. If an `AGENTS.md` already exists, merge into it and show your user the diff instead of overwriting.
6. Write `CLAUDE.md`. If one exists, add the `@AGENTS.md` line to it instead of replacing it.
7. If row 15 is yes, write `Home.md` from its template, linking every MOC.
8. If row 17 is yes, add the deny rule to `.claude/settings.json` in the vault, merging into any existing `permissions.deny` array. Claude Code asks before any write under `.claude/`; tell your user to approve it.
9. If row 4 is yes, carry out the approved backfill plan: add a Connections section to each note in the plan, opening with its Maps of Content line; add the approved direct links with their sentences, and the back-link in each target note; add each note to its MOC only if it is one a reader would go back to. Change nothing else in an existing note, and add no tags to it.
10. If row 16 is yes, commit again, so the build and the backfill each sit in their own commit.
11. Start a new Claude Code session in the vault (the rules load at session start) and run the tests.

## `AGENTS.md`

Fill in the placeholders, keep one of the two layout blocks, delete lines for parts the user left out, and keep the rest word for word.

````markdown
# AGENTS.md

Guidance for Claude Code in this vault. `CLAUDE.md` imports this file, so every session starts with it loaded.

## What this vault is

An Obsidian vault of markdown notes kept by [OWNER] for [PURPOSE]. It isn't a software project; there is nothing to build, lint or test.

Leave `.obsidian/` alone. It holds Obsidian's own settings, and an edit there can break the app.

## Layout

Personal profile:

```
Home.md                   # Entry point: the MOCs and the most used notes
Resources/                # Permanent notes, one subfolder per note type
  MOC - [Theme].md        # Maps of Content: one index per theme
  Books/                  # Book and long-document summaries, every topic on one shelf
  Briefs/                 # Analysis and commentary notes
  Personal/               # First-person frameworks: finances, career, health, values
  Technical/              # Tool and protocol knowledge you sit down to read
  Field Guides/           # Quick-reference how-tos and cheatsheets consulted for a fast answer
  References/             # Source documents and companion notes about them
  People/                 # Profiles of people
  Video_Summaries/        # Video summaries, named YYYY-MM-DD Speaker - Show.md
  Podcasts/               # Podcast episode summaries, named YYYY-MM-DD Show.md
  Templates/              # Note skeletons, never content
```

Work profile:

```
Home.md                   # Entry point: the MOCs, active workstreams and the people met most
MOCs/                     # Maps of Content: MOC - [Theme].md, one index per theme
Inbox/                    # Raw captures waiting to be filed
Meetings/                 # One note per meeting: YYYY-MM-DD <meeting name>.md
People/                   # One note per colleague, professional facts only
Workstreams/              # One note per ongoing thread of work
Decisions/                # ADR-NNN <title>.md, one per decision
Briefs/                   # Research and analysis
Status/                   # Weekly status reports, one per ISO week: YYYY-Www.md
Daily/                    # One note per day: YYYY-MM-DD.md
Templates/                # Note skeletons, never content
```

Either profile:

```
Drafts/                   # Work in progress; nothing here is final
Designs/                  # Dated design docs for things being built: YYYY-MM-DD <topic>.md
  Plans/                  # Implementation plans for those designs
  Observations/           # Dated readouts of a running system, taken as evidence for a pending decision
Infra/                    # Notes about the vault itself and its tooling
  ADRs/                   # Decision records about the vault: ADR-NNN <title>.md, indexed by README.md
Ideas/                    # Unfinished ideas and open threads, date-prefixed
Prompts/                  # Reusable prompts and pre-prompts
Mail_Drop/                # Files the owner drops in for Claude to read
Library/                  # Kept source material: books, PDFs, handbooks
Jots/                     # Quick captures, throwaway
Travel/                   # Per-trip notes, kept as a log
Projects/                 # Pointers to projects whose working files live outside the vault
```

**Folders and MOCs answer different questions.** A note's folder says what it is (a book summary, a meeting, a decision). Its MOC links say what it is about. When adding a note, pick the folder that matches its type, then link it to the MOC for its theme, up to the cap below.

**A new note goes in the folder that matches its type**, never in a parent folder's root, and never in a new folder while a fitting one exists. In the personal profile, Field Guides and Technical differ by purpose, not subject: Technical holds analysis read start to finish, Field Guides holds the recipe consulted mid-task. A folder stays flat until it passes about 40 notes; then it may split by topic.

## Maps of Content

Each MOC is a file named `MOC - [Theme].md`. Its opening paragraph says what the theme covers and what it leaves out, so a note can be routed by reading it. Each note links up to its MOC; the MOC links down to the note with a one-line description. This keeps the link count linear: notes don't need to link to every related note, because the MOC already groups them.

Current MOCs:
- `MOC - [Theme]` - [one line on what it covers]

**When adding a note:**
1. Decide which MOC it belongs to.
2. Add `**Maps of Content:** [[MOC - Theme]]` as the first line of its Connections section.
3. Add the note to the right section of that MOC with a one-line description, if it is one a reader would go back to.
4. Link the note directly to another note only when the connection can be explained in a sentence ("this decision came out of that meeting"), and write that sentence beside the link. Add the back-link in the other note's Connections section.

**MOC cap: [CAP] per note.** A note that seems to belong in more is usually two notes, or one whose subject isn't settled.

**An MOC is a highlight reel.** It links the notes a reader goes back to, roughly a fifth of a theme, not every note that touches it. A note doesn't need an MOC entry to belong to a theme; its own up-link does that. Until a theme passes about 20 notes, list them all; after that, cut peripheral entries as it grows, before splitting it.

**Splitting an MOC.** When one MOC's sections each hold enough notes to stand alone, split it into sub-MOCs and turn the original into a parent. A parent MOC links only to its sub-MOCs and related parents; notes link to the most specific sub-MOC, never to the parent.

**Exempt from MOCs and Connections:** Templates/, Inbox/, Daily/, Status/, Drafts/, Designs/, Ideas/, Prompts/, Mail_Drop/, Jots/, Library/ and Travel/. These are logs, raw captures, source material or tooling. In the work profile, a meeting links up to its workstream instead of an MOC, and a person is reached from Home and from the workstreams they own.

**Orphans.** A note outside the exempt folders with no MOC link and no inbound link is an orphan. When asked to audit the vault, list the orphans and propose a home for each, or ask whether it should go.

## Note conventions

**Every new note follows its template:** [TEMPLATE RULE]. Frontmatter fields are [FIELDS], then the template's sections.

**Wikilinks.** Use `[[Note Title]]` for every internal reference: the filename without extension or folder. Obsidian resolves links across the whole vault. Link a named vault note on its first mention in each section, and check that the target exists before linking.

**Never invent a fact to fill a field.** A date comes from the source, the file, or the `date` command; a link, a number or a quote comes from somewhere it was read. If it isn't known, say so or leave the field blank.

**Tags.** A note's last line carries its type tag: the singular name of its type folder in lowercase, with hyphens for spaces (`#book`, `#field-guide`, `#meeting`, `#decision`). Notes in exempt folders carry none.

**Home.md** links every MOC and the handful of notes used most. Keep it short; it is a doorway, not an index of everything.

## Standing rules

**Nothing leaves the machine without a yes.** Before anything goes out under [OWNER]'s name (an email, a chat post, a calendar change, an edit to a shared file, a push), show the exact text and wait for an explicit yes in the same conversation. A yes covers that one action.

**Connectors are read-only** unless [OWNER] says otherwise in the same message.

**Nothing from this vault goes to an outside service** (a gist, a paste site, a share link, a third-party tool) that [OWNER] hasn't approved for it.

**Respect sensitivity markings.** A note or source marked confidential is summarized at the level asked for, never quoted wholesale. When someone prefers not to be recorded, write down what was decided, never a transcript of what they said.

**Weekly status** goes to [STATUS AUDIENCE]: at least three highlights with the biggest items first, then run-the-business work, then risks.

## Folders with their own rules

**Drafts/** holds unfinished writing. Never link to a draft from a permanent note.

**Designs/** holds build artifacts only: the design doc for a thing being built, its plan in `Plans/`, readouts in `Observations/`. A decision with no thing being built goes to Decisions/ (work) or `Infra/ADRs/` (vault decisions). An implementation log may be appended to a design doc once the work ships.

**Inbox/** holds raw captures. File each one into its type folder, or delete it, when it is processed.

**Ideas/** holds deliberately unfinished threads, named `YYYY-MM-DD <idea>.md`.

**Mail_Drop/** and **Jots/** are throwaway source material. Read them when asked, never write to them unless told, and never cite them from a permanent note.

**Library/** is the opposite of Mail_Drop: kept source material, cited from the summary notes built on it. Read-only unless told to add a file.

**Travel/** holds one note per trip, kept as a log.
````

## `CLAUDE.md`

```markdown
See AGENTS.md for vault structure and conventions.

@AGENTS.md
```

The `@AGENTS.md` line is Claude Code's import syntax: the file's contents load into every session started in the vault. Keeping the rules in `AGENTS.md` lets other agents that read that filename use them too.

## Templates

Each template goes in the profile's `Templates/` folder under the name shown. Replace the frontmatter fields with the row 11 answer, except in the MOC template.

### `MOC Template.md` (both profiles)

```markdown
---
Date Added:
Topic: ""
---

# MOC - Theme

A map of vault notes on [what the theme covers]. It leaves out [what a reader might expect here but should look for elsewhere, and where].

## [First section]

- [[Note Title]] - one line on what the note covers and why someone would reopen it

## Related MOCs

- [[MOC - Other Theme]] - one line on where the two themes meet
```

### `Resource Template.md` (personal)

```markdown
---
Date Added:
Topic: ""
---

# Title

## Key Takeaways

## Source Link

## Related Topics

## Connections

**Maps of Content:** [[MOC - Theme]]

## Notes
```

### `Meeting Template.md` (work)

```markdown
---
Date Added:
Topic: ""
---

# YYYY-MM-DD Meeting name

## Attendees

## Decisions

## Action Items

- [ ] Owner - action - due date

## Notes

## Connections

**Workstream:** [[Workstream name]]
```

### `Person Template.md` (work)

```markdown
---
Date Added:
Topic: ""
---

# Name

## Role

## Reporting Line

## How They Like Information

## Decisions They Own

## Connections

**Maps of Content:** [[MOC - Theme]]
```

### `Workstream Template.md` (work)

```markdown
---
Date Added:
Topic: ""
---

# Workstream name

## Goal

## Status

## Owners

## Open Questions

## Log

- YYYY-MM-DD - entry (newest last)

## Connections

**Maps of Content:** [[MOC - Theme]]
```

### `Decision Template.md` (work)

```markdown
---
Date Added:
Topic: ""
---

# ADR-NNN Title

## Context

## Options

## Decision

## Consequences

## Connections

**Maps of Content:** [[MOC - Theme]]
```

### `Weekly Status Template.md` (work)

```markdown
---
Date Added:
Topic: ""
---

# Status YYYY-Www

For [STATUS AUDIENCE].

## Highlights

## Run the Business

## Risks
```

### `Daily Template.md` (work)

```markdown
---
Date Added:
Topic: ""
---

# YYYY-MM-DD

## Meetings

## Done

## Carried Over
```

## `Home.md`

```markdown
# Home

## Maps of Content

- [[MOC - Theme]] - one line on what it covers

## Most used

- [[Note Title]] - one line on why it is here
```

In the work profile, add an `## Active workstreams` section listing each workstream note.

## `.claude/settings.json`

If the file exists, add the two entries to its `permissions.deny` array instead of replacing the file.

```json
{
  "permissions": {
    "deny": [
      "Read(./.obsidian/**)",
      "Edit(./.obsidian/**)"
    ]
  }
}
```

## Tests

Run these in a new Claude Code session started in the vault, and report each result to the user. Skip a test whose part the user left out.

1. List the vault's top-level folders and the profile's type folders. Every folder chosen in Phase 1 is there, and nothing that was left out.
2. Ask, in the new session: "Where would a summary of a book on gardening go, and what has to happen when it's added?" (work profile: "a note from today's budget meeting"). The answer names the right folder, the template, and the Maps of Content line or workstream link, which shows `AGENTS.md` loaded.
3. Paste a few paragraphs from any article and ask Claude to file it as a note (work profile: paste rough meeting notes naming a decision and an owner). It goes into the right type folder with the template's frontmatter and sections, its Connections section links up correctly, and the MOC or workstream gained a line for it.
4. Ask Claude to read `.obsidian/app.json`. The deny rule refuses it.
5. If row 4 was yes, open three existing notes from the backfill plan. Each has a Connections section matching the plan, and every direct link has its back-link. Nothing else in them changed (`git diff` on the backfill commit shows only added Connections lines).
6. If row 13 was yes, ask Claude to email a one-line summary of the vault to a colleague. It shows the exact text and waits for a yes rather than sending, or says it has no way to send.
7. If row 16 was yes, `git log --oneline` shows the baseline commit, the build, and the backfill as separate commits.
8. In Obsidian, open an MOC. Its links resolve, and the graph view shows notes linked up to it.

Delete the test notes and their MOC entries afterwards, unless the user wants to keep them.

## Notes for the builder

- Tested on macOS with Claude Code in headless mode and user settings switched off, in three throwaway vaults, every choice changed from its default somewhere. A personal vault adopted with a cap of one and an extra frontmatter field; a second personal vault adopted five loose notes in two folders with backfill and git; a new, empty work vault with Home, git and a weekly-status audience. In each, one session built the vault from this recipe and a fresh session ran the tests: 2, 3, 4 and 6 passed in both of the later vaults, 5 and 7 passed in the backfilled one, and each build's report on unclear steps went back into this recipe. Test 8 needs Obsidian open and hasn't been run. Headless sessions can't write under `.claude/`, so the deny rule was added by hand, as a user approving the prompt would.
- The deny rule stops Claude's file tools. A shell command can still read `.obsidian/`; the rule in `AGENTS.md` covers that case by instruction only.
- Rename a note or folder inside Obsidian, which rewrites the links to it. A rename done in the shell or by Claude leaves those links broken.
- The standing rules are instructions, not locks. For a hard stop on a connector that can send, add its sending tools to the `permissions.deny` list in `.claude/settings.json` as well.
- The rules are deliberately few. When Claude keeps making the same mistake, add one sentence to `AGENTS.md` naming the rule; when a rule stops mattering, delete it. A rulebook nobody prunes stops being read.
