---
name: distill
description: Move durable learnings from this session's notebook into project files, and retire stale ones
disable-model-invocation: true
---
Run `monet-notebook list` to see this session's open learnings. If there are none, say so in one line and stop.

Otherwise, distill them. Decide for each one:

- **Durable:** it will help future work in this project. Place it by how a future agent finds it, then retire it with `monet-notebook retire <id> --reason "<where it went>"`, unless it still guides the current work.
  - `.claude/LEARNINGS.md` loads into every session in this project. Keep it to short instructions that should change behavior on every turn.
  - A ledger task's `retrospective.md` is read when someone works on a related task. Use it for lessons about that undertaking.
  - The project's docs, for project knowledge a search would find.
- **Current:** it still guides the work now but will not matter later. Keep it open.
- **Stale:** it no longer holds or is not worth keeping. Retire it.

Read each destination before you edit it and merge with what is there. Keep `.claude/LEARNINGS.md` short: merge duplicates and remove lines that no longer hold. Write only non-sensitive synthesis: leave out credentials and private transcript text. Changes to CLAUDE.md, skills, code, or files outside the project belong to `/monet:promote`, which the user runs.

End with one line per learning: its id, the decision, and where it went.
