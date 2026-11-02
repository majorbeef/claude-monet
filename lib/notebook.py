"""The session notebook: learnings that last one session and survive compaction.

Also holds the plugin's settings lookup and the project learnings path.
Standard library only; runs on Python 3.9+.
"""
import datetime
import hashlib
import json
import os
import re
import time
import uuid
from pathlib import Path

# ---------------------------------------------------------------------------
# Settings

def option(name, default=None):
    """A setting from MONET_<NAME>, then the plugin option CLAUDE_PLUGIN_OPTION_<NAME>, then default."""
    key = name.upper()
    for var in (f"MONET_{key}", f"CLAUDE_PLUGIN_OPTION_{key}"):
        value = os.environ.get(var)
        if value not in (None, ""):
            return value
    return default



PROJECT_LEARNINGS = ".claude/LEARNINGS.md"

# ---------------------------------------------------------------------------
# Session notebook: learnings that last one session and survive compaction.
#
# Each session has an append-only JSONL file of events:
#   {"op": "add", "id": "<12 hex>", "content": "...", "supersedes": [...], "ts": "..."}
#   {"op": "retire", "ids": [...], "reason": "...", "ts": "..."}
# Folding the events gives the open learnings.

ID_PATTERN = re.compile(r"^[a-f0-9]{12}$")


def notebook_dir():
    return Path(os.environ.get("MONET_NOTEBOOK_DIR") or Path.home() / ".claude" / "monet" / "notebooks")


def session_id(explicit=None):
    sid = explicit or os.environ.get("MONET_SESSION_ID")
    if not sid:
        raise NotebookError(
            "No session id. MONET_SESSION_ID is set by the monet SessionStart hook; "
            "start a new session with the plugin enabled, or pass --session."
        )
    if not re.fullmatch(r"[A-Za-z0-9_.-]+", sid):
        raise NotebookError(f"Invalid session id: {sid}")
    return sid


class NotebookError(Exception):
    pass


def notebook_path(sid):
    return notebook_dir() / f"{sid}.jsonl"


def now_iso():
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


def read_events(sid):
    path = notebook_path(sid)
    if not path.exists():
        return []
    events = []
    for line in path.read_text().splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError:
            continue  # a torn final line from a crash; skip it
    return events


def append_event(sid, event):
    path = notebook_path(sid)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "a") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def fold(events):
    """Return (open learnings in insertion order, all learnings by id)."""
    learnings = {}
    for event in events:
        if event.get("op") == "add" and event.get("id"):
            learnings[event["id"]] = dict(event, open=True)
            for old in event.get("supersedes") or []:
                if old in learnings:
                    learnings[old]["open"] = False
                    learnings[old]["retiredBy"] = event["id"]
        elif event.get("op") == "retire":
            for old in event.get("ids") or []:
                if old in learnings:
                    learnings[old]["open"] = False
                    learnings[old]["retireReason"] = event.get("reason")
    return [l for l in learnings.values() if l["open"]], learnings


def new_id(content):
    return hashlib.sha256(f"{content}\0{time.time_ns()}\0{uuid.uuid4()}".encode()).hexdigest()[:12]


def add_learning(sid, content, supersedes=()):
    content = " ".join(content.split())
    if not content:
        raise NotebookError("A learning cannot be empty")
    _, everything = fold(read_events(sid))
    for old in supersedes:
        if old not in everything:
            raise NotebookError(f"No learning with id {old} in this session")
    lid = new_id(content)
    append_event(sid, {"op": "add", "id": lid, "content": content, "supersedes": list(supersedes), "ts": now_iso()})
    return lid


def retire_learnings(sid, ids, reason=None):
    open_, everything = fold(read_events(sid))
    open_ids = {l["id"] for l in open_}
    for lid in ids:
        if lid not in everything:
            raise NotebookError(f"No learning with id {lid} in this session")
        if lid not in open_ids:
            raise NotebookError(f"Learning {lid} is already retired")
    append_event(sid, {"op": "retire", "ids": list(ids), "reason": reason, "ts": now_iso()})


def open_learnings(sid):
    return fold(read_events(sid))[0]


def learning_line(learning):
    return f"[{learning['id']}] {learning['content']}"


DISTILL_INSTRUCTION = """Distill the open learnings of this session. Decide for each one:

- **Durable:** it will help future work in this project. Place it by how a future agent finds it, then retire it with `monet-notebook retire <id> --reason "<where it went>"`, unless it still guides the current work.
  - `.claude/LEARNINGS.md` loads into every session in this project. Keep it to short instructions that should change behavior on every turn.
  - A ledger task's `retrospective.md` is read when someone works on a related task. Use it for lessons about that undertaking.
  - The project's docs, for project knowledge a search would find.
- **Current:** it still guides the work now but will not matter later. Keep it open.
- **Stale:** it no longer holds or is not worth keeping. Retire it.

Read each destination before you edit it and merge with what is there. Keep `.claude/LEARNINGS.md` short: merge duplicates and remove lines that no longer hold. Write only non-sensitive synthesis: leave out credentials and private transcript text. Changes to CLAUDE.md, skills, code, or files outside the project belong to `/monet:learnings promote`, which the user runs."""


def distill_prompt(learnings):
    return DISTILL_INSTRUCTION + "\n\nOpen learnings:\n" + "\n".join(learning_line(l) for l in learnings)


NOTEBOOK_USAGE = """Session notebook (monet): record a hard-won learning the moment you find it, with `monet-notebook add "<learning>"`: a falsified hypothesis, a pitfall, how to reach a service, a user correction, what to do differently now. Write each one so it stands alone after compaction (exact paths, commands, and the reason). Skip ordinary progress and anything already in the code or docs. Replace a learning that changed with `monet-notebook add "<new>" --supersedes <id>`; retire one that no longer holds with `monet-notebook retire <id>`. Open learnings are restored after every compaction."""


def compaction_packet(learnings):
    if not learnings:
        return ""
    return (
        "## Session notebook (restored after compaction)\n\n"
        "Learnings recorded earlier in this session. Apply each one while it holds; ids are in brackets. "
        "`monet-notebook show <id>` shows when and why one was recorded.\n\n"
        + "\n".join(learning_line(l) for l in learnings)
        + "\n\nAt the next natural pause, distill them (`/monet:learnings distill`) so durable ones move to project files."
    )
