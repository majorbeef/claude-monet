# Running an organizational process

Choose a process when the exchange between perspectives can change the result. A direct question or one capable owner is often enough. Work within the current goal and authority; selecting a skill grants no new permission.

## How a process runs in Claude Code

The session that runs the process is its chair unless the skill names another. The people in a process are this plugin's role subagents (`monet:<role>`, for example `monet:architecture-prosecutor`), started with the Agent tool. The process words map to Claude Code like this:

- **Staff a person**: start the role subagent with a self-contained brief: the question, the constraints, the sources to read, and what to return. A subagent sees none of this conversation, so the brief carries everything it needs.
- **Independent first positions**: start the participants in parallel, in one message, each with the same facts and none with another's answer.
- **Shared thread** (for people who must answer each other's positions): the chair collects every position verbatim into one message, or into a file in the governing ledger task when it is long, and sends that same message to each participant. Use SendMessage to continue a participant that is still available, so it keeps its own earlier reasoning; otherwise start the role again with its first position included. Repeat only while a round changes something.
- **Mail, reply, or ask a person directly**: one brief to one subagent and its answer.
- **Operator sign-off**: ask the operator at the authority boundary, following [sign-off](../sign-off/SKILL.md).

Each subagent's report is lossy: it holds only what the subagent chose to say and can state a belief as fact. The chair checks the claims that decide the result.

## Put responsibility before ceremony

Name who is accountable for the result and who may make the decision. A chair coordinates the exchange; the operator keeps every decision outside the current authority. Ask the operator at a real authority boundary rather than requiring a vote on every within-scope judgment.

Choose the perspectives the case needs, not a fixed board or every role in the catalog. Every subagent costs a full model run, so start with the smallest useful board: one participant, plus a `scientific-skeptic` only when the result needs challenge. Add a perspective only when the case's risk names it or the operator asks, and say why in one line when you do. A participant is advisory unless the brief explicitly gives it a bounded change to make; only roles that may write (`implementation-engineer`, `technical-writer`) get edit work.

## Give the exchange one useful home

Keep the current owner, decision, next action, evidence and unresolved questions in the governing ledger task's ordinary files when the process outlives this conversation, or in the conversation when it does not. Reuse existing records rather than create another workflow state store.

## Recover and conclude honestly

When a participant fails or returns nothing useful, distinguish missing critical input from an optional view. Retry with a sharper brief, narrow the result or report the blocker; make coverage limits visible. A reply, agreement and completed work are different facts.

End with the process's observable result, what was verified and what remains uncertain. A process with several participants closes with a short note on what helped or hindered it, which feeds the task's `retrospective.md` when there is one. Use a deeper retrospective only when the experience warrants it. Keep durable follow-up in a ledger task; nothing in a conversation is durable scheduling.
