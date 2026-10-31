---
name: ralph
description: "Run or continue bounded fresh-context Ralph iterations over a goal or prepared ledger task."
disable-model-invocation: true
---

# Ralph

Ralph is a bounded loop of fresh implementation engineers. Each iteration starts a new headless Claude Code session (`claude -p`, running as the `monet:implementation-engineer` subagent) with an empty context, which reads the repository, makes one coherent increment, checks it, and exits. The repository, and a ledger task when there is one, is the only memory between iterations; you set the goal, bound the run, and own review and integration.

Its value is a fresh context every iteration, which a subagent inside this session cannot give, and the loop's bounds, mutation scoring, and stop conditions are code that prose cannot run reliably. So Ralph runs as the `monet-ralph` command (on the Bash tool's PATH while this plugin is enabled).

## Prepare the run

1. Write the goal so a fresh engineer can choose a useful increment without inventing product decisions: the outcome, acceptance criteria, relevant paths, constraints, likely failure modes, and the fastest checks. An engineer that needs an operator decision stops and names it.
2. Adapt the increment prompt with the goal's terms: [`simple-increment.md`](references/simple-increment.md) for a goal you own, or [`ledger-increment.md`](references/ledger-increment.md) for a prepared ledger task. Save it beside the goal (in the ledger task's directory when there is one).
3. Confirm the working tree is in a state you can review afterwards (ideally clean), and that the operator accepts the permission mode the workers will run with (default `acceptEdits`; workers cannot run unapproved shell commands in that mode unless the project's settings allow them).
4. Check the prompt: `monet-ralph --goal-file <goal> --prompt-file <prompt> --iterations 1 --dry-run`.

## Run it

```bash
# Over a goal you own
monet-ralph --goal-file goal.md --prompt-file increment.md --iterations 5 --context docs/spec.md

# Over a prepared ledger task; stops when its Status becomes done, blocked, or cancelled
monet-ralph --task .ledger/<id> --goal-file .ledger/<id>/goal.md --prompt-file .ledger/<id>/increment.md --iterations 8
```

Arguments after `--` go to every `claude -p` call (for example `-- --allowedTools "Bash(npm test:*)"`). A long run belongs in the background: run it with the Bash tool's background mode, or tell the operator the command to run in their own terminal.

The command prints a JSON summary: `status` (`completed`, `stopped`, or `failed`), `stopReason` (`task-done`, `task-blocked`, `task-cancelled`, or `low-mutation`), and per-iteration mutation scores, turns, and cost. In ledger mode each worker's final report is appended to the task's `ralph-log.md`. A low-mutation stop is an escape hatch, not a judgment that the goal is complete.

## Iteration contract

Each engineer reads the current repository, picks the single most valuable increment, implements it, runs the relevant checks, and stops. Engineers never commit, push, merge, deploy, publish, reset, or review.

## After a batch

1. Inspect the repository and run the relevant checks yourself; fix ordinary problems in your own session.
2. Read and apply [`code-review`](../code-review/SKILL.md) to the batch's changes.
3. Read and apply [`operator-sign-off`](../operator-sign-off/SKILL.md) for a code sign-off, unless the operator waived sign-off for this run (as for unattended overnight loops); say so in the report.
4. Decide whether another batch is useful. Commit, and close a ledger task, only with the operator's authority.

Record progress or evidence in the ledger only when a later session needs it.
