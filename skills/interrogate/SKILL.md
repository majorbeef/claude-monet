---
name: interrogate
description: "Interrogate me about a plan, decision, or idea until we share complete understanding, optionally recording settled domain terms, design knowledge, and approved ADRs as we go."
argument-hint: "[subject] [record]"
disable-model-invocation: true
---

# Interrogate

Interrogate me about $ARGUMENTS (or, if no subject is given, the plan, decision, or idea in our current conversation).

## The interview

Map the subject as a **design tree**: every decision branches into the decisions that depend on it. Establish the scope, then work the tree in rounds. The **frontier** is every in-scope decision whose prerequisites are settled now. Ask the whole frontier in each round, with your recommended answer for every question, and put questions with unresolved prerequisites in a later round. Then wait for my answers.

Ask each round with `AskUserQuestion`: put what you found and why it matters in your message, and ask the questions as short structured choices, four per call, with as many calls as the frontier needs. Use prose only for a question whose answer does not fit a few options.

Facts are your job: use tools or subagents (such as `monet:repository-archaeologist`) instead of asking me for what can be established. If fact-finding is still running, leave only its dependent branch open and continue with the rest. Decisions are my job: never answer my side of the interview.

After each round, recompute the tree and frontier. Name out-of-scope branches and empirical questions that need research, a prototype, or a hand-off. Use no question cap and no "clear enough" shortcut.

The interview is complete only when the in-scope frontier is empty. Before you present the summary, give it to a role subagent with the right lens (for example `monet:vp-of-product` for what to build, `monet:chief-architect` for system shape), without the conversation, and ask which branch is missing; open a new round for any real gap. Then summarize the shared understanding, remaining hand-offs, and scope boundary, and wait for my explicit confirmation.

## Recording (only when asked)

By default, create or modify no files. When I ask you to record (for example by adding `record` to the command), curate the project's domain and design docs (`docs/` by default) as decisions settle. Read each page before you change it and merge with what is there.

- Record resolved domain terms in the domain-language page, in the [domain-language format](../domain-modeling/references/DOMAIN-LANGUAGE-FORMAT.md), free of implementation detail.
- Fold broader reusable design knowledge into existing pages, and create a page only for a distinct subject with value beyond this task. Synthesize; never copy the conversation.
- Keep task-specific specifications, tickets, and plans in their ledger or repository owners.
- Offer an ADR only when the decision is hard to reverse, surprising without context, and the result of a real trade-off. Say why it qualifies and get approval before writing it, following the repository's convention or the [ADR format](../domain-modeling/references/ADR-FORMAT.md).

This skill authorizes no commits, publication, deployment, or implementation, and no work beyond the interview until I confirm the summary.

## Finish

After I confirm, report the settled design and scope, any doc pages and ADRs changed, the open research, prototype, or hand-off branches, and the next workflow if I want to continue (for example `/monet:to-spec`).
