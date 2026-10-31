# claude-monet

`monet` is a Claude Code plugin adapted from [apple-pi](https://github.com/z3z1ma/apple-pi), a personal coding harness built on `pi`. It keeps the apple-pi parts that fit Claude Code: the engineering and team-process skills, the role catalog as subagents, a session notebook whose learnings survive compaction, the `.ledger/` task workbench, fresh-context Ralph loops, and optional RTK output compression.

It is a selective remake, not a port. Parts that Claude Code already covers, or that depend on Pi's runtime, were left out ([see below](#what-was-left-out)).

## Install

```
/plugin marketplace add majorbeef/claude-monet
/plugin install monet@claude-monet
```

To try it from a local checkout without installing: `claude --plugin-dir /path/to/claude-monet`.

Requirements: `python3` (3.9+, standard library only) and `git`. RTK rewriting also needs the [`rtk`](https://github.com/rtk-ai/rtk) binary.

## What you get

### Skills (`/monet:<name>`)

| Kind | Skills |
| --- | --- |
| Idea to delivery | `interrogate`, `interrogate-to-design`, `domain-modeling`, `codebase-design`, `to-spec`, `to-tickets`, `wayfinder`, `implement`, `tdd`, `prototype`, `ralph` |
| Engineering disciplines | `code-review`, `diagnosing-bugs`, `research`, `resolving-merge-conflicts`, `improve-codebase-architecture`, `handbook-writing`, `operator-sign-off`, `review-document` |
| Team processes | `peer-consultation`, `decision-review`, `tiger-team`, `handoff`, `incident-response`, `operating-review`, `retrospective`, `pre-mortem`, `prioritization`, `release-readiness`, `discovery-workshop`, `onboarding`, `failure-exercise`, `due-diligence`, `experiment-cycle` |
| Notebook | `reflect`, `distill`, `promote` |

Claude picks most skills on its own when they fit. These run only when you type them: `interrogate`, `interrogate-to-design`, `to-spec`, `to-tickets`, `wayfinder`, `implement`, `improve-codebase-architecture`, `ralph`, `reflect`, `distill`, `promote`.

The team-process skills ran on Pi's mail and org runtime in apple-pi. Here the session running the skill chairs, and the participants are role subagents: independent first positions run in parallel, and the chair relays positions between them when they must answer each other. The mapping lives in [`skills/handbook-writing/references/processes.md`](skills/handbook-writing/references/processes.md).

### Role subagents (`monet:<role>`)

35 roles from apple-pi's catalog, such as `architecture-prosecutor`, `scientific-skeptic`, `staff-security-engineer`, `implementation-engineer`, and `new-team-member`. Each role keeps the model and effort apple-pi recommended for Claude. Advisory roles cannot edit files. `coordinator` was dropped because it only worked inside Pi's org runtime.

### Session notebook

Claude records hard-won learnings as it works: a falsified hypothesis, a pitfall, or a correction you made. It records them with `monet-notebook add "..."`.

- After every compaction, the open learnings are put back into context, so they survive when the transcript is summarized.
- After about 500k new tokens, a Stop hook asks Claude once to reflect and record what it learned. It includes the tool calls that failed since the last reflection.
- `/monet:distill` moves durable learnings into `.claude/LEARNINGS.md` (loaded at every session start) or a ledger task's `retrospective.md`, and retires the rest.
- `/monet:promote` proposes moving proven learnings into files you own, such as `CLAUDE.md`, skills, and docs. It waits for your approval before changing anything.

Notebooks are stored per session in `~/.claude/monet/notebooks/`.

### Ledger

`.ledger/` is a folder of task bundles: `task.md` and `retrospective.md`, plus the spec, tickets, and evidence that `to-spec`, `to-tickets`, and `wayfinder` add.

```
monet-ledger add --title "Rate-limit the export API" --description "Token bucket per tenant"
monet-ledger status <task-id> in-progress     # planning | ready | in-progress | done | cancelled
monet-ledger list
```

`done` and `cancelled` move the bundle to `.ledger/history/`. Closing a task while the session still has open learnings is refused once, so they get distilled into the task's retrospective first. When a project has a `.ledger/`, its working agreement is added to Claude's context at session start.

### Ralph loops

`monet-ralph` runs a bounded loop of fresh `claude -p` sessions. Each one runs as `monet:implementation-engineer`, makes one increment, and exits. The repository, and optionally a ledger task, carries state between rounds. The loop stops after N rounds, when the ledger task is `done`, `blocked`, or `cancelled`, or when two rounds in a row barely change anything. See [`skills/ralph/SKILL.md`](skills/ralph/SKILL.md).

```
monet-ralph --goal-file goal.md --prompt-file increment.md --iterations 5
```

### Document review page

`monet-review <file.md>` opens a Markdown document as a review page in your browser. You select text to comment, mark it 👍 or ❓, mark it for deletion, or suggest a rewrite. You can also comment on or rewrite whole blocks, add an overall comment, and pick a verdict. When you press **Send to Claude**, Claude gets every annotation with its `path:line` and the quoted text. The file itself is never changed; Claude applies the feedback.

Claude uses it through the `review-document` skill, and `operator-sign-off` uses it for document sign-offs. You can also ask for it directly: "let me review docs/spec.md". The page is served only on `127.0.0.1` behind a one-time token. It renders Markdown with bundled copies of marked and DOMPurify, and raw HTML in the document is shown as text. Mermaid diagrams load Mermaid from jsDelivr, but only when the document has one.

### RTK (off by default)

When it's on, Bash commands go through `rtk rewrite`, so test runners, git, and build tools return compressed output. Commands that your permission rules already allow are auto-approved. Everything else still goes through the normal permission prompt. Add a `# verbatim` comment to a command to get exact output. If you already ran `rtk init -g`, leave this off, because RTK installed its own hook.

## Configuration

Set these in `/config` (plugin options), or override them with environment variables:

| Option | Env override | Default | |
| --- | --- | --- | --- |
| `rtk` | `MONET_RTK=1` (or `RTK_ENABLED=1`) | off | RTK rewriting |
| `reflect_every_tokens` | `MONET_REFLECT_EVERY_TOKENS` | 500000 | Tokens between reflections; `0` turns them off |
| | `MONET_NOTEBOOK_DIR` | `~/.claude/monet/notebooks` | Where notebooks are stored |

## What was left out

| apple-pi | In Claude Code |
| --- | --- |
| `interns` (explore/research), `tasks`, `ask-user-question`, `notify`, `/btw` | Built-in subagents, background tasks, `AskUserQuestion`, notification hooks, `/btw` |
| `session-search` | Not ported; `monet-notebook show` covers notebook provenance |
| `pi-exec`, saved programs, `branch-search`, `pair-programmer`, `organization`/`session-state` | Not ported (Pi runtime); team processes use subagents instead |
| `browser-pages` (`sign_off_*`, `explain_change`) | `sign_off_document` → `monet-review` (no "ask the agent" from the page); code and ledger sign-offs write a review file and ask with `AskUserQuestion`; `explain-change` dropped |
| `code-context`, `home-search-guard`, `change-reflection`, `wiki`/`llm-wiki` | Left out by choice; domain docs go in `docs/` |
| `tmux-sessions`, `terse-tools`, `input-editor`, `prompt-stash`, Agent World, provider tweaks | Out of scope |

## Development

```
python3 -m unittest discover -s tests   # CLIs, hooks, the review server, and the Ralph loop (with a fake claude)
claude plugin validate .
```

Layout: `skills/`, `agents/`, `hooks/` (`hooks.json` plus Python hooks), `bin/` (on Claude's Bash PATH while the plugin is enabled), `lib/monet.py` (shared notebook and ledger logic), `lib/review.py` and `lib/web/` (the review page and its vendored libraries).

## License

MIT, as apple-pi. See [`LICENSE`](LICENSE) and [`THIRD_PARTY_NOTICES.md`](THIRD_PARTY_NOTICES.md).
