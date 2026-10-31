"""SessionStart: export the session id for monet-notebook, and add monet's context.

On every start, resume, clear, and compaction it adds:
  - the project's .claude/LEARNINGS.md
  - how to use the session notebook
  - the ledger working agreement, when the project has a .ledger/
  - the RTK note, when RTK rewriting is on
After a compaction it also restores this session's open learnings.
"""
import json
import os
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import monet  # noqa: E402
import rtk_rewrite  # noqa: E402


def main():
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        event = {}
    sid = event.get("session_id") or ""
    source = event.get("source") or "startup"
    project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or os.getcwd())

    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file and sid:
        with open(env_file, "a") as f:
            f.write(f"export MONET_SESSION_ID={shlex.quote(sid)}\n")

    sections = []
    learnings_file = project / monet.PROJECT_LEARNINGS
    if learnings_file.is_file():
        text = learnings_file.read_text().strip()
        if text:
            sections.append(
                f"## Project learnings\n\nLearnings from earlier sessions in this project, kept in "
                f"`{monet.PROJECT_LEARNINGS}`. Apply them; the user's instructions and CLAUDE.md take precedence.\n\n{text}"
            )

    sections.append(monet.NOTEBOOK_USAGE)

    ledger_root = monet.find_root(project)
    if (ledger_root / ".ledger").is_dir():
        sections.append("## Ledger\n\n" + monet.LEDGER_CONTRACT)

    if rtk_rewrite.enabled():
        sections.append(rtk_rewrite.PROMPT)

    if source == "compact" and sid:
        try:
            packet = monet.compaction_packet(monet.open_learnings(sid))
        except monet.NotebookError:
            packet = ""
        if packet:
            sections.append(packet)

    print(
        json.dumps(
            {"hookSpecificOutput": {"hookEventName": "SessionStart", "additionalContext": "\n\n".join(sections)}}
        )
    )


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # never break session start
        print(f"monet session_start: {error}", file=sys.stderr)
