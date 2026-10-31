---
name: research
description: Investigate a question against high-trust primary sources and capture the findings as a Markdown file in the repo. Use when the user wants a topic researched, docs or API facts gathered, or external reading kept out of the main context.
---

Give a bounded external question to a research subagent (the built-in `general-purpose` agent with web access). Name the relevant versions and primary sources, and supply source material when access depends on the root's integrations or credentials. The subagent keeps reading out of the main context and returns once; its summary is lossy and can miss or misread details.

Ask it to:

1. Investigate against **primary sources**: official docs, source code, specs, and first-party APIs. Follow each claim to the source that owns it.
2. Return findings with citations and enough source identity to revisit each claim.
3. Mark missing evidence **Not verified**, and distinguish what it checked from what it believes.

The root verifies the details that decide the outcome against the cited sources. When a finding decides something costly or hard to reverse, also give a `monet:scientific-skeptic` subagent the findings and their citations, and ask which decisive claim the sources do not support. Then write the findings to one Markdown file. Match the repository's existing convention for such notes. Otherwise use the active ledger task for undertaking-specific research, or the repository's `docs/` for reusable knowledge. If neither fits, choose a sensible location and report it.

When the question has independent parts, start several research subagents in parallel with distinct questions and readable material, then reconcile their answers into the same artifact. Write a script when source acquisition and result reduction benefit from a program; ordinary parallel reading needs only subagents.
