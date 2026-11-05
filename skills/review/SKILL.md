---
name: review
description: Open a Markdown document on the browser review page so the user can comment on it, then act on their feedback. With no file, write one from this session first.
argument-hint: "[file.md] [focus]"
disable-model-invocation: true
---

# Review a document

Arguments: $ARGUMENTS

## Pick the document

If the first argument is a path to a file, review that file. The page renders Markdown only: for any other file, say so in one line and stop. The rest of the arguments say what the user wants to look at; use them for the `--note`.

Otherwise, all the arguments are the focus, and you write the document from this session:

1. Take what the conversation is working toward that needs the user's judgment: the plan, proposal, design, or decision under discussion, or a summary of what was done and what is still open. If the focus names something, write about that. If the conversation has nothing substantial to review, say so in one line and ask what to review.
2. Write it for a reader who skipped the conversation:
   - The first lines say what the document is for and what the user is asked to decide.
   - Headings state claims ("Store sessions in SQLite"), not topics ("Storage").
   - Choices show each option, what it costs, and which you recommend.
   - Mark what is settled and what is still open. Use only what the session established; write open questions as open, and don't invent requirements.
   - Add a Mermaid diagram when a flow or structure is easier to see than to read.
3. Save it as `.monet/reviews/<YYYY-MM-DD>-<slug>.md` in the project and review that file. `monet-review` keeps `.monet/` out of git, so never commit it or save the document anywhere else unless the user asks. If the user wants to keep it, offer to move it into the project's docs.

## Open the review page

`monet-review` (on the Bash tool's PATH while this plugin is enabled) serves the Markdown file as a rendered page on `127.0.0.1` and waits until the user presses **Send to Claude**. On the page they select text to comment, mark 👍 looks good or ❓ clarify, mark for deletion, or suggest a rewrite; comment on or rewrite whole blocks; add an overall comment; and choose a verdict: approve, approve with notes, request changes, or dismiss.

1. Start it **in the background** (Bash with `run_in_background: true`), because it runs until the user finishes. Never add `&` or run it in the foreground: Claude Code only reports the feedback when a background task exits.

   ```bash
   monet-review path/to/spec.md --note "One sentence: what you need from the reviewer"
   ```

   It opens the browser and prints the page's address on its first line. Tell the user in one or two sentences what the document is and what you need, and give the address in case the browser did not open. Then stop and wait; do not continue work that depends on the verdict.
2. When the command exits, read its output. It holds the verdict, the overall comment, then **Questions** (❓ marks and comments that ask something) and **Changes and notes**, each with its kind, `path:line` anchor, and quoted text (with the replacement for a suggested rewrite), and each rewritten block before and after.
3. **Answer questions before editing.** A question asks for your answer, not for an edit, and the user may disagree with your answer. For each question, and any question in the overall comment, answer in the conversation: what the passage means or why it says what it does, and, when there's a choice, the options with your recommendation. Then stop and wait for the user's reply. Don't decide on their behalf, and don't change the parts a question covers until they've answered.
4. Apply the changes yourself; the file was not changed. Treat a suggested rewrite or rewritten block as the user's intended wording. Changes that no open question touches can go in while you wait on the answers. Once the questions are settled, apply what was agreed. Report what you changed, and what you left and why. An approval covers only what the user saw.
5. If the answers changed the document in ways the user hasn't seen, offer another review round.

Exit code 2 means `--timeout` passed before the user finished. If the page says the session ended, the user can copy their feedback from the Finish dialog and paste it into the conversation.
