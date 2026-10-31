---
name: review-document
description: "Open a Markdown document (a spec, plan, proposal, or README) as a review page in the operator's browser, where they annotate it and give a verdict. Use when the operator asks to review or sign off on a document, and for the document step of operator-sign-off."
argument-hint: "<path.md> [what you need from the reviewer]"
---

# Review a document in the browser

`monet-review` (on the Bash tool's PATH while this plugin is enabled) serves the Markdown file as a rendered page on `127.0.0.1` and waits until the operator presses **Send to Claude**. On the page they select text to comment, mark 👍 looks good or ❓ clarify, mark for deletion, or suggest a rewrite; comment on or rewrite whole blocks; add an overall comment; and choose a verdict: approve, approve with notes, request changes, or dismiss.

1. Make the document decidable first (see [operator-sign-off](../operator-sign-off/SKILL.md) and its [document reference](../operator-sign-off/references/document.md)). The page shows the file as it is on disk.
2. Start it **in the background** (Bash with `run_in_background: true`), because it runs until the operator finishes:

   ```bash
   monet-review path/to/spec.md --note "One sentence: what you need from the reviewer"
   ```

   It opens the browser and prints the page's address on its first line. Tell the operator in one or two sentences what the document is and what you need, and give the address in case the browser did not open. Then stop and wait; do not continue work that depends on the verdict.
3. When the command exits, read its output. It holds the verdict, the overall comment, each annotation with its kind, `path:line` anchor, and quoted text (with the replacement for a suggested rewrite), and each rewritten block before and after.
4. Apply the feedback yourself; the file was not changed. Treat a suggested rewrite or rewritten block as the operator's intended wording, and a ❓ as a passage to make clearer. Report what you changed, and what you left and why. An approval covers only what the operator saw.

Exit code 2 means `--timeout` passed before the operator finished. If the page says the session ended, the operator can copy their feedback from the Finish dialog and paste it into the conversation.
