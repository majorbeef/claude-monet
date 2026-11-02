# Document sign-off

**Goal:** the operator can decide on what the document says, from the document alone. Here the document is the presentation, so the work is in the document before you ask.

## Make the document decidable

When you wrote the document, check it the way the operator will meet it:

- **The first lines** say what the document is for and what the operator is asked to decide.
- **Headings state claims** ("Store sessions in SQLite"), not topics ("Storage"), so the outline alone tells the story.
- **Options carry consequences.** A choice shows each option, what it costs, and which you recommend.
- **Settled and open are marked**, so attention goes to the open parts.
- **A picture** carries any flow, structure, or sequence the prose describes.

Fix what fails before you ask for sign-off. The cold reader must be able to say, from the document alone, what it proposes and what is being decided.

When someone else wrote the document, leave it as it is: the cold reader still reads it, and what lost the reader goes into your framing in the conversation.

## Frame the review

One document, one judgment: sign-off means the document is complete enough to sign; a decision means the options are on the page. When the question spans a ledger undertaking, sign off on the task instead.

## Open the review page

`monet-review` (on the Bash tool's PATH while this plugin is enabled) serves the Markdown file as a rendered page on `127.0.0.1` and waits until the operator presses **Send to Claude**. On the page they select text to comment, mark 👍 looks good or ❓ clarify, mark for deletion, or suggest a rewrite; comment on or rewrite whole blocks; add an overall comment; and choose a verdict: approve, approve with notes, request changes, or dismiss.

1. Start it **in the background** (Bash with `run_in_background: true`), because it runs until the operator finishes:

   ```bash
   monet-review path/to/spec.md --note "One sentence: what you need from the reviewer"
   ```

   It opens the browser and prints the page's address on its first line. Tell the operator in one or two sentences what the document is and what you need, and give the address in case the browser did not open. Then stop and wait; do not continue work that depends on the verdict.
2. When the command exits, read its output. It holds the verdict, the overall comment, each annotation with its kind, `path:line` anchor, and quoted text (with the replacement for a suggested rewrite), and each rewritten block before and after.
3. Apply the feedback yourself; the file was not changed. Treat a suggested rewrite or rewritten block as the operator's intended wording, and a ❓ as a passage to make clearer. Report what you changed, and what you left and why. An approval covers only what the operator saw.

Exit code 2 means `--timeout` passed before the operator finished. If the page says the session ended, the operator can copy their feedback from the Finish dialog and paste it into the conversation.
