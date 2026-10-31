# Ledger task sign-off

**Goal:** the operator can approve the undertaking as a whole: what will be built or was built, in what order, at what risk, and how done is known. The bundle's own files must make the case; include the ticket dependency graph as a Mermaid diagram or an ordered list in your message.

## Name the boundary

There are two sign-offs, and the operator reads differently for each:

- **A plan**, before implementation. Ask when the specification and tickets are written.
- **An outcome**, before closure. Ask when the evidence and the retrospective are written.

Say which one this is, and point at the document to read first when it is not `task.md`.

## Make the bundle decidable

For a plan:

- `task.md` opens with the intent and the acceptance criteria, so the operator knows what done means before reading how.
- The ticket order is explained where it is not obvious, and the riskiest ticket is named.
- Decisions still open are listed as open.

For an outcome:

- Each acceptance criterion is matched to its evidence.
- What was not verified, and what surprised, are named.

The cold reader must be able to say, from the bundle alone, what will be built (or was built), in what order, and how done is known.

## After the verdict

Implementation and status changes follow the governing workflow and the scope of the approval.
