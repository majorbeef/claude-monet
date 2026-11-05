# claude-monet

`monet` is a Claude Code plugin: engineering and team-decision skills, role subagents, a session notebook whose learnings survive compaction, a `.ledger/` task workbench, and a browser review page for Markdown documents.

## Install

```
/plugin marketplace add majorbeef/claude-monet
/plugin install monet@claude-monet
```

To try it from a local checkout without installing: `claude --plugin-dir /path/to/claude-monet`.

Requirements: `python3` (3.9+, standard library only) and `git`.

## What you get

### Skills (`/monet:<name>`)

| Kind | Skills |
| --- | --- |
| Idea to delivery | `interrogate`, `domain-modeling`, `codebase-design`, `to-spec`, `to-tickets`, `implement`, `tdd`, `prototype` |
| Engineering | `code-review`, `diagnosing-bugs`, `research`, `resolving-merge-conflicts`, `improve-codebase-architecture`, `sign-off` |
| Team decisions | `decision-review`, `pre-mortem`, `retrospective` |
| Notebook and tasks | `learnings` (`record`, `distill`, `promote`), `ledger` (`list`, `add`, `resume`, `close`) |

Skills that start several subagents, or that start a multi-step workflow, run only when you type them: `code-review`, the team-decision skills, `interrogate`, `to-spec`, `to-tickets`, `implement`, `improve-codebase-architecture`, `learnings`, and `ledger`. Claude picks the rest (`tdd`, `diagnosing-bugs`, `research`, `domain-modeling`, `codebase-design`, `prototype`, `resolving-merge-conflicts`, `sign-off`) on its own when they fit.

Boards start small: one reviewer plus a `scientific-skeptic`, growing only when the risk calls for it or you ask. The session running a multi-agent skill chairs it, and the participants are role subagents: independent first positions run in parallel, and the chair relays positions between them when they must answer each other. The conventions live in [`skills/shared/processes.md`](skills/shared/processes.md).

### Role subagents (`monet:<role>`)

18 roles, the ones the skills call on, such as `architecture-prosecutor`, `scientific-skeptic`, `staff-security-engineer`, `implementation-engineer`, and `new-team-member`. Most run on Sonnet at medium effort. Four deep-judgment roles stay on Opus (`chief-architect`, `architecture-prosecutor`, `staff-security-engineer`, `scientific-skeptic`), and two routine roles on Haiku. Change a role's `model` and `effort` lines in `agents/` to rebalance. Advisory roles cannot edit files.

### Session notebook

Claude records hard-won learnings as it works: a falsified hypothesis, a pitfall, or a correction you made. It records them with `monet-notebook add "..."`.

- After every compaction, the open learnings are put back into context, so they survive when the transcript is summarized.
- Optional (off by default): after a set number of new tokens, a Stop hook asks Claude once to reflect and record what it learned, listing the tool calls that failed since the last reflection. `/monet:learnings record` does the same on demand.
- `/monet:learnings distill` moves durable learnings into `.claude/LEARNINGS.md` (loaded at every session start) or a ledger task's `retrospective.md`, and retires the rest.
- `/monet:learnings promote` proposes moving proven learnings into files you own, such as `CLAUDE.md`, skills, and docs. It waits for your approval before changing anything.

Notebooks are stored per session in `~/.claude/monet/notebooks/`.

### Ledger

`.ledger/` is a folder of task bundles: `task.md` and `retrospective.md`, plus the spec, tickets, and evidence that `to-spec` and `to-tickets` add. It's local working state and never committed: `monet-ledger` writes `.ledger/.gitignore` so git ignores the whole folder.

Claude doesn't start a ledger on its own. Use `/monet:ledger`:

```
/monet:ledger                                  # list live tasks and suggest next steps
/monet:ledger add rate-limit the export API    # start a task (and the ledger, the first time)
/monet:ledger resume export                    # pick a task up by id or title words
/monet:ledger close export                     # fill in outcome and retrospective, then archive
```

Claude runs `monet-ledger` underneath; you can too:

```
monet-ledger add --title "Rate-limit the export API" --description "Token bucket per tenant"
monet-ledger status <task-id> in-progress     # planning | ready | in-progress | done | cancelled
monet-ledger list
```

`done` and `cancelled` move the bundle to `.ledger/history/`. Closing a task while the session still has open learnings is refused once, so they get distilled into the task's retrospective first. When a project has a `.ledger/`, its working agreement is added to Claude's context at session start.

### Document review page

`monet-review <file.md>` opens a Markdown document as a review page in your browser. You select text to comment, mark it 👍 or ❓, mark it for deletion, or suggest a rewrite. You can also comment on or rewrite whole blocks, add an overall comment, and pick a verdict. When you press **Send to Claude**, Claude gets every annotation with its `path:line` and the quoted text. The file itself is never changed; Claude applies the feedback.

Claude uses it through the `sign-off` skill for document sign-offs. You can also ask for it directly: "let me review docs/spec.md". The page is served only on `127.0.0.1` behind a one-time token. It renders Markdown with bundled copies of marked and DOMPurify, and raw HTML in the document is shown as text. Mermaid diagrams load Mermaid from jsDelivr, but only when the document has one.

## Keeping token use down

**Generated-file guard (on by default).** A hook stops Claude from reading a large generated file whole: lockfiles, `node_modules/`, `dist/`, `build/`, `target/`, minified bundles, source maps, and snapshots over 20 KB. Claude is told to `grep` it or read a slice instead. Small files pass (a library's type definitions in `node_modules` are often worth reading), and so do reads that ask for a slice. To read a whole one anyway, ask Claude to, and turn the guard off for that session with `MONET_GENERATED_GUARD=0`.

**`LEARNINGS.md` budget.** `.claude/LEARNINGS.md` loads into every session. Once it passes about 1,500 tokens, the session-start hook asks Claude to offer a trim.

**Status line.** `monet-statusline` shows the model, how full the context window is (yellow past 50%, red with a `/compact?` hint past 75%), the prompt-cache hit rate, and the session cost:

```
Opus · ▓▓▓░░░░░░░ 34% ctx · cache 92% · $1.23
```

Plugins can't set the main status line, so install it once: ask Claude to run `monet-statusline --install`. It copies the script to `~/.claude/monet/` and sets `statusLine` in `~/.claude/settings.json`, backing the file up first. It won't replace a status line you already have unless you add `--force`.

**Shorter replies.** Claude Code's built-in Concise style cuts preamble and recaps from every reply: `/output-style concise`.

**Compact command output with RTK.** For noisy commands (test runners, `git`, build tools), [RTK](https://github.com/rtk-ai/rtk) rewrites them into compact equivalents and ships its own Claude Code hook:

```
brew install rtk     # or see RTK's install guide
rtk init -g          # installs RTK's PreToolUse hook for Claude Code
```

RTK's hook only auto-approves a rewritten command when your permission rules already allow the original; everything else still goes through the normal prompt.

**Habits that need no tooling:** `/clear` between unrelated tasks, `/compact <what to keep>` before the window fills, `/context` to see what is using it, and turning off MCP servers you don't use.

## Configuration

Set these in `/config` (plugin options), or override them with environment variables:

| Option | Env override | Default | |
| --- | --- | --- | --- |
| `generated_guard` | `MONET_GENERATED_GUARD=0` | on | Block whole reads of large generated files (threshold: `MONET_GENERATED_GUARD_BYTES`, default 20000) |
| `reflect_every_tokens` | `MONET_REFLECT_EVERY_TOKENS` | 0 (off) | Tokens between automatic reflections (500000 is a reasonable value) |
| | `MONET_NOTEBOOK_DIR` | `~/.claude/monet/notebooks` | Where notebooks are stored |

## Development

```
python3 -m unittest discover -s tests   # CLIs, hooks, the review server, the status line, and skill links
claude plugin validate .
```

Layout: `skills/`, `agents/`, `hooks/` (`hooks.json` plus Python hooks), `bin/` (on Claude's Bash PATH while the plugin is enabled), `lib/monet.py` (shared notebook and ledger logic), `lib/review.py` and `lib/web/` (the review page and its vendored libraries).

## License

MIT. See [`LICENSE`](LICENSE) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
