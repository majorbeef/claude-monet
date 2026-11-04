---
name: ledger
description: Work with the project's .ledger/ task workbench. `list` shows live tasks; `add` starts a task (and the ledger, if the project has none); `resume` picks a task up; `close` finishes or cancels one.
argument-hint: "list | add <what> | resume <task> | close <task> [cancelled]"
disable-model-invocation: true
---

# Ledger

The first argument picks the step: $ARGUMENTS. With no argument, run **list**.

`monet-ledger` is on the Bash tool's PATH while this plugin is enabled. If the project has no `.ledger/` yet, or you have not seen the ledger working agreement in this session, run `monet-ledger contract` first and follow it.

The ledger is never committed. `monet-ledger` keeps it out of git with `.ledger/.gitignore`, so never stage, commit, or ask about committing its files.

A `<task>` can be a task id, a `.ledger/<id>` path, or words from its title. Match words against `monet-ledger list`; if more than one task fits, show the matches and ask which.

## list

Run `monet-ledger list`. Show each live task on one line: title, status, and id. Then suggest the likely next step for each, in a few words (shape it, start it, finish it), based on its status and its `task.md` Current State.

If the project has no ledger, say so in one line and offer `/monet:ledger add <what>` to start one.

## add

The rest of the arguments describe the work. If they are empty, use the work under discussion in this conversation; if there is none, ask what the task is for.

1. Check `.ledger/INDEX.md` for a live task that already owns this work. If one does, say which and offer to resume it instead.
2. Write a title (one line, a goal rather than a topic) and a one-line description that a later search would match. Run `monet-ledger add --title "..." --description "..."`.
3. Replace the placeholders in the new `task.md` with what is known from the arguments and the conversation:
   - **Intent:** the goal, why it matters, and acceptance criteria when they are known.
   - **Current State:** what is settled, what is still open, and the next step.
   - **Outcome:** leave as pending.
   Do not invent requirements. Write open questions as open.
4. Report the task's path and its open questions. It stays `planning` until intent, approach, and acceptance criteria are settled.

## resume

1. Find the task. Read its `task.md`, then the other files in its bundle (spec, tickets, notes) that bear on the next step, and the `retrospective.md` of any closed task in `.ledger/history/INDEX.md` that looks related.
2. Summarize in a few lines: the goal, where it stands, what is open, and the next step.
3. If the status is `ready` and the user wants to start, run `monet-ledger status <id> in-progress`. If it is `planning`, help settle what is still open before implementation starts.
4. While working, keep **Current State** in `task.md` current, so a later session can pick the task up from the file alone.

## close

Closes a task as `done`, or as `cancelled` when that word follows the task.

1. Find the task and read its `task.md`.
2. Fill in **Outcome**: what was delivered or why the task stopped, and where the result lives (commits, PRs, docs). Update **Current State** to match.
3. Fill in `retrospective.md`: what mattered, the lessons worth finding again for related work, and improvements. Keep it short; write "None" for a section with nothing worth keeping.
4. Run `monet-ledger status <id> done` (or `cancelled`). If it exits with code 3, this session still has open notebook learnings: run the **distill** step of [`learnings`](../learnings/SKILL.md), putting lessons about this task into its `retrospective.md`. Then run the command again with `--learnings-distilled`.
5. Report where the task was archived, under `.ledger/history/`.
