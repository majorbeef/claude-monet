"""PreToolUse(Read, Bash): stop whole-file reads of large generated files.

Lockfiles, dependency and build folders, minified bundles, source maps, and
snapshots are rarely worth reading whole, and one read can cost tens of thousands
of tokens. A read is blocked only when the file matches one of those patterns,
is larger than the threshold (20 KB by default), and is read whole: a Read with a
`limit`, or `head`/`tail`/`grep` in Bash, passes. Small files always pass, so
reading a library's type definitions in node_modules still works.

Turn it off with MONET_GENERATED_GUARD=0 or the plugin's `generated_guard` option;
change the threshold with MONET_GENERATED_GUARD_BYTES. Fails open.
"""
import json
import os
import re
import shlex
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "lib"))
import notebook  # noqa: E402  (settings lookup)

DEFAULT_THRESHOLD = 20_000

LOCKFILES = {
    "package-lock.json", "npm-shrinkwrap.json", "yarn.lock", "pnpm-lock.yaml", "bun.lockb", "bun.lock",
    "Cargo.lock", "poetry.lock", "uv.lock", "Pipfile.lock", "Gemfile.lock", "composer.lock", "go.sum",
    "mix.lock", "pubspec.lock", "Podfile.lock", "flake.lock", "packages.lock.json",
}
GENERATED_DIRS = {
    "node_modules", "dist", "build", ".next", ".nuxt", ".svelte-kit", ".turbo", ".parcel-cache",
    "coverage", ".nyc_output", "__pycache__", ".venv", "venv", ".tox", ".mypy_cache", ".pytest_cache",
    "target", "__snapshots__", ".gradle", "DerivedData", "Pods",
}
GENERATED_SUFFIXES = (".min.js", ".min.css", ".min.mjs", ".map", ".snap", ".bundle.js", ".chunk.js")
# Commands that print a whole file. head/tail/grep/wc/jq read a slice or a summary, so they pass.
DUMP_COMMANDS = {"cat", "less", "more", "bat", "nl"}


def generated_reason(path):
    """Why this path counts as generated, or None."""
    p = Path(path)
    if p.name in LOCKFILES:
        return "a lockfile"
    if p.name.endswith(GENERATED_SUFFIXES):
        return "minified, a source map, or a snapshot"
    hit = next((part for part in p.parts[:-1] if part in GENERATED_DIRS), None)
    if hit:
        return f"inside `{hit}/`, which holds generated or installed files"
    return None


def threshold():
    try:
        return int(os.environ.get("MONET_GENERATED_GUARD_BYTES") or DEFAULT_THRESHOLD)
    except ValueError:
        return DEFAULT_THRESHOLD


def check_path(path, cwd):
    """A block message for a whole read of this path, or None."""
    reason = generated_reason(path)
    if not reason:
        return None
    full = Path(path) if os.path.isabs(path) else Path(cwd or ".") / path
    try:
        size = full.stat().st_size
    except OSError:
        return None
    if size <= threshold():
        return None
    return (
        f"Blocked a whole-file read of `{path}` ({size // 1024} KB, about {size // 4:,} tokens): it is {reason}. "
        f"Read only what you need: search it (`grep -n '<name>' {shlex.quote(path)}`), read a slice "
        f"(Read with offset and limit, or `head`), or check the source that generates it. "
        f"If the whole file is needed, say why and ask the user to allow it."
    )


def bash_paths(command):
    """Files that a dump command in this shell command would print whole."""
    try:
        words = shlex.split(command, posix=True)
    except ValueError:
        return []
    paths, dumping = [], False
    for word in words:
        if word in ("|", "||", "&&", ";") or word.endswith((";", "|")):
            dumping = False
            continue
        if not dumping:
            dumping = os.path.basename(word) in DUMP_COMMANDS
            continue
        if word.startswith("-") or word in (">", ">>", "<"):
            continue
        paths.append(word)
    # A pipe into a filter means the output is cut down, so only bare dumps count.
    if re.search(r"\|\s*(grep|rg|head|tail|wc|jq)\b", command):
        return []
    return paths


def decide(event):
    """The hook's JSON output for this event, or None to let it run."""
    tool = event.get("tool_name")
    tool_input = event.get("tool_input") or {}
    cwd = event.get("cwd")
    message = None
    if tool == "Read":
        if tool_input.get("limit"):
            return None
        path = tool_input.get("file_path")
        if isinstance(path, str):
            message = check_path(path, cwd)
    elif tool == "Bash":
        command = tool_input.get("command")
        if isinstance(command, str):
            message = next((m for m in (check_path(p, cwd) for p in bash_paths(command)) if m), None)
    if not message:
        return None
    return {
        "hookSpecificOutput": {
            "hookEventName": "PreToolUse",
            "permissionDecision": "deny",
            "permissionDecisionReason": message,
        }
    }


def main():
    if notebook.option("generated_guard", "1").strip().lower() in ("0", "false", "no", "off"):
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
        print(f"monet generated_guard: {error}", file=sys.stderr)
