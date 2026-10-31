"""PreToolUse(Bash): route commands through `rtk rewrite` so RTK compresses noisy output.

Off unless RTK is enabled (MONET_RTK=1, RTK_ENABLED=1, or the plugin's `rtk` option)
and the `rtk` binary is installed. Fails open: any problem runs the original command.

`rtk rewrite` exit codes: 0 rewritten and allowed by the user's permission rules
(auto-approve), 1 no RTK equivalent, 2 a deny rule matched (leave it to Claude
Code), 3 rewritten but needs the normal permission prompt.

A command containing a `# verbatim` comment is never rewritten.
"""
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import monet  # noqa: E402

PROMPT = (
    "RTK may rewrite Bash commands and summarize their output. Add a trailing `# verbatim` comment to a "
    "command when the next step needs its exact stdout or stderr, such as a precise diff or a full stack trace."
)
VERBATIM = re.compile(r"(^|\s)#\s*verbatim\b")


def enabled():
    flag = monet.option("rtk") or os.environ.get("RTK_ENABLED")
    return monet.truthy(flag or "") and shutil.which("rtk") is not None


def decide(event, run=subprocess.run):
    """Return the hook's JSON output for this event, or None to leave the call alone."""
    if event.get("tool_name") != "Bash":
        return None
    tool_input = event.get("tool_input") or {}
    command = tool_input.get("command")
    if not isinstance(command, str) or not command.strip():
        return None
    if command.lstrip().startswith("rtk ") or "<<" in command or VERBATIM.search(command):
        return None
    env = {k: v for k, v in os.environ.items() if k != "RTK_REWRITE_HOST"}
    try:
        proc = run(["rtk", "rewrite", command], capture_output=True, text=True, timeout=2, env=env)
    except (OSError, subprocess.SubprocessError):
        return None
    rewritten = (proc.stdout or "").strip()
    if proc.returncode not in (0, 3) or not rewritten or rewritten == command:
        return None
    output = {"hookEventName": "PreToolUse", "updatedInput": dict(tool_input, command=rewritten)}
    if proc.returncode == 0:
        output["permissionDecision"] = "allow"
        output["permissionDecisionReason"] = "RTK rewrite of a command your permission rules allow"
    return {"hookSpecificOutput": output}


def main():
    if not enabled():
        return
    try:
        event = json.load(sys.stdin)
    except json.JSONDecodeError:
        return
    result = decide(event)
    if result:
        print(json.dumps(result))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:  # fail open
        print(f"monet rtk_rewrite: {error}", file=sys.stderr)
