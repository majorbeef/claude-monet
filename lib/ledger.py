"""The ledger: the project's task workbench under .ledger/.

Standard library only; runs on Python 3.9+.
"""
import datetime
import os
import re
import shutil
import time
import unicodedata
import uuid
from contextlib import contextmanager
from pathlib import Path

# ---------------------------------------------------------------------------
# Ledger: the project's task workbench under .ledger/

SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
TASK_ID = re.compile(r"^\d{12}-[a-z0-9]+(?:-[a-z0-9]+)*$")
LIVE_STATUSES = ("planning", "ready", "in-progress")
CLOSED_STATUSES = ("done", "cancelled")
STATUSES = LIVE_STATUSES + CLOSED_STATUSES
LIVE_HEADING = "# Task ledger"
HISTORY_HEADING = "# Task history"


class LedgerError(Exception):
    pass


LEDGER_CONTRACT = """The ledger is this project's task workbench. `.ledger/` holds one directory per undertaking, `.ledger/INDEX.md` lists live tasks, and closed tasks move to `.ledger/history/`. The repository owner decides whether it is committed or shared.

Use a task when work needs to be written down, resumed, handed off, or understood later; small, coherent work needs none. Before you add a task, check the index for one that already owns the work. Create one with `monet-ledger add --title "..." --description "..."`.

A task's `task.md` holds its intent, status, current state, and outcome. Keep the status current with `monet-ledger status <task> <status>`: `planning` until intent, approach, and acceptance criteria are settled, then `ready`, then `in-progress` once implementation starts; `done` and `cancelled` archive it (only after edits to the bundle are committed). Add other files only when they serve the work; the workflow that creates a file owns its format. Keep `retrospective.md` to what mattered and the lessons worth retrieving later.

Repository documentation and tests stay authoritative for product behavior; the ledger holds task-specific context."""


def _two(n):
    return f"{n:02d}"


def _stamp(now):
    return (
        f"{now.year}{_two(now.month)}{_two(now.day)}{_two(now.hour)}{_two(now.minute)}",
        f"{now.year}-{_two(now.month)}-{_two(now.day)}",
    )


def _one_line(value, label, limit):
    line = " ".join(value.split())
    if not line or len(line) > limit or "\n" in value or "\r" in value:
        raise LedgerError(f"{label} must be one line between 1 and {limit} characters")
    return line


def slug_from(title, requested=None):
    text = (requested or "").strip() or title
    text = unicodedata.normalize("NFKD", text)
    text = "".join(c for c in text if not unicodedata.combining(c)).lower()
    slug = re.sub(r"[^a-z0-9]+", "-", text).strip("-")[:80].rstrip("-")
    if not SLUG.match(slug):
        raise LedgerError("slug must contain lowercase letters, numbers, and single hyphens only")
    return slug


def task_template(title, date):
    return f"""Status: planning
Created: {date}
Updated: {date}

# {title}

## Intent

Pending shaping.

## Current State

Planning; pending shaping.

## Outcome

Pending shaping.
"""


def retrospective_template(date):
    return f"""Status: pending
Created: {date}
Updated: {date}

# Retrospective

## What Mattered

Pending completion of the undertaking.

## Learnings

Pending completion of the undertaking.

## Improvements

Pending completion of the undertaking.
"""


def write_atomic(path, content):
    path = Path(path)
    tmp = path.parent / f".{os.getpid()}.{uuid.uuid4().hex}.tmp"
    try:
        with open(tmp, "x") as f:
            f.write(content)
        if path.exists():
            os.chmod(tmp, path.stat().st_mode & 0o777)
        os.replace(tmp, path)
    finally:
        if tmp.exists():
            tmp.unlink()


@contextmanager
def ledger_lock(root, timeout=10.0):
    """A directory lock so two sessions never interleave index writes."""
    lock = Path(root, ".ledger", ".lock")
    lock.parent.mkdir(exist_ok=True)
    deadline = time.monotonic() + timeout
    while True:
        try:
            lock.mkdir()
            break
        except FileExistsError:
            try:
                if time.time() - lock.stat().st_mtime > 120:  # stale lock from a crash
                    lock.rmdir()
                    continue
            except FileNotFoundError:
                continue
            if time.monotonic() > deadline:
                raise LedgerError("A ledger transaction is busy; try again")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            lock.rmdir()
        except FileNotFoundError:
            pass


def _check_dir(path, label):
    if path.is_symlink() or (path.exists() and not path.is_dir()):
        raise LedgerError(f"{label} must be a non-symlink directory")


def _read_index(path, heading, entry_path, duplicate_error):
    current = f"{heading}\n"
    if path.exists():
        if path.is_symlink() or not path.is_file():
            raise LedgerError(f"{path} must be a regular non-symlink file")
        current = path.read_text()
    legacy = heading.title() if heading != heading.title() else heading
    if not re.search(rf"^{re.escape(heading)}\s*$", current, re.M) and not re.search(
        rf"^{re.escape(legacy)}\s*$", current, re.M
    ):
        raise LedgerError(f"{path} must contain a '{heading}' heading")
    if f"`{entry_path}`" in current:
        raise LedgerError(duplicate_error)
    return current


def _row_pattern(task_path):
    statuses = "|".join(re.escape(s) for s in LIVE_STATUSES)
    return re.compile(rf"^-\s+`{re.escape(task_path)}`\s+—\s+(?:(?:{statuses})\s+—\s+)?(.+)$", re.M)


def _remove_row(content, task_path):
    pattern = _row_pattern(task_path)
    match = pattern.search(content)
    if not match:
        return content, None
    content = pattern.sub("", content, count=1)
    return re.sub(r"\n{3,}", "\n\n", content), match.group(1).strip()


def _title_from(task_md, fallback):
    match = re.search(r"^#\s+(.+)$", task_md, re.M)
    return match.group(1).strip() if match else fallback


def _with_status(task_md, status):
    if re.search(r"^Status:\s+\S+\s*$", task_md, re.M):
        task_md = re.sub(r"^Status:\s+\S+\s*$", f"Status: {status}", task_md, count=1, flags=re.M)
    else:
        task_md = f"Status: {status}\n{task_md}"
    today = datetime.date.today().isoformat()
    if re.search(r"^Updated:\s+.*$", task_md, re.M):
        task_md = re.sub(r"^Updated:\s+.*$", f"Updated: {today}", task_md, count=1, flags=re.M)
    return task_md


def parse_task_id(value):
    value = value.strip().replace("\\", "/").rstrip("/")
    value = re.sub(r"/task\.md$", "", value, flags=re.I)
    parts = [p for p in value.split("/") if p]
    task_id = parts[-1] if parts else ""
    if not TASK_ID.match(task_id):
        raise LedgerError("task must be a YYYYMMDDhhmm-kebab-slug id or .ledger path")
    if "history" in parts:
        raise LedgerError(f"The ledger task is already archived: .ledger/history/{task_id}")
    return task_id


def find_root(start):
    """The nearest directory at or above start that holds .ledger/, else the git top level, else start."""
    start = Path(start).resolve()
    for d in (start, *start.parents):
        if (d / ".ledger").is_dir():
            return d
    for d in (start, *start.parents):
        if (d / ".git").exists():
            return d
    return start


def add_task(root, title, description, slug=None, now=None):
    root = Path(root).resolve()
    title = _one_line(title, "title", 160)
    description = _one_line(description, "description", 400)
    slug = slug_from(title, slug)
    stamp, date = _stamp(now or datetime.datetime.now())
    task_id = f"{stamp}-{slug}"
    ledger = root / ".ledger"
    _check_dir(ledger, ".ledger")
    ledger.mkdir(exist_ok=True)
    bundle = ledger / task_id
    task_path = f".ledger/{task_id}/task.md"
    with ledger_lock(root):
        if bundle.exists():
            raise LedgerError(f"The ledger task already exists: .ledger/{task_id}")
        if (ledger / "history" / task_id).exists():
            raise LedgerError(f"The ledger task is already archived: .ledger/history/{task_id}")
        index = ledger / "INDEX.md"
        current = _read_index(index, LIVE_HEADING, task_path, f"The ledger index already contains {task_path}")
        next_index = current.rstrip("\n") + f"\n\n- `{task_path}` — planning — {title} — {description}\n"
        bundle.mkdir()
        try:
            (bundle / "task.md").write_text(task_template(title, date))
            (bundle / "retrospective.md").write_text(retrospective_template(date))
            write_atomic(index, next_index)
        except Exception:
            shutil.rmtree(bundle, ignore_errors=True)
            raise
    return {"taskId": task_id, "bundlePath": f".ledger/{task_id}", "taskPath": task_path}


def set_status(root, task, status):
    root = Path(root).resolve()
    task_id = parse_task_id(task)
    if status not in STATUSES:
        raise LedgerError(f"status must be one of {', '.join(STATUSES)}")
    with ledger_lock(root):
        if status in LIVE_STATUSES:
            return _update_live(root, task_id, status)
        return _archive(root, task_id, status)


def _live_task(root, task_id):
    ledger = root / ".ledger"
    _check_dir(ledger, ".ledger")
    if (ledger / "history" / task_id).exists():
        raise LedgerError(f"The ledger task is already archived: .ledger/history/{task_id}")
    bundle = ledger / task_id
    if not bundle.is_dir():
        raise LedgerError(f"Requested ledger task not found: .ledger/{task_id}")
    task_file = bundle / "task.md"
    if not task_file.is_file():
        raise LedgerError(f"The ledger task is missing task.md: .ledger/{task_id}/task.md")
    return ledger, bundle, task_file


def _update_live(root, task_id, status):
    ledger, _, task_file = _live_task(root, task_id)
    task_path = f".ledger/{task_id}/task.md"
    task_md = task_file.read_text()
    index = ledger / "INDEX.md"
    current = _read_index(
        index, LIVE_HEADING, f".ledger/history/{task_id}/task.md", "The ledger index has an invalid history row"
    )
    pattern = _row_pattern(task_path)
    match = pattern.search(current)
    summary = match.group(1).strip() if match else _title_from(task_md, task_id)
    row = f"- `{task_path}` — {status} — {summary}"
    next_index = pattern.sub(lambda _: row, current, count=1) if match else current.rstrip("\n") + f"\n\n{row}\n"
    write_atomic(task_file, _with_status(task_md, status))
    try:
        write_atomic(index, next_index)
    except Exception:
        write_atomic(task_file, task_md)
        raise
    return {"taskId": task_id, "status": status, "taskPath": task_path}


def _archive(root, task_id, status):
    ledger, bundle, task_file = _live_task(root, task_id)
    history = ledger / "history"
    _check_dir(history, ".ledger/history")
    live_path = f".ledger/{task_id}/task.md"
    hist_path = f".ledger/history/{task_id}/task.md"
    task_md = task_file.read_text()
    live_index_file = ledger / "INDEX.md"
    hist_index_file = history / "INDEX.md"
    live_index = _read_index(live_index_file, LIVE_HEADING, hist_path, "The ledger index has an invalid history row")
    hist_index = _read_index(hist_index_file, HISTORY_HEADING, hist_path, f"History index already contains {hist_path}")
    next_live, summary = _remove_row(live_index, live_path)
    summary = summary or _title_from(task_md, task_id)
    next_hist = hist_index.rstrip("\n") + f"\n\n- `{hist_path}` — {status} — {summary}\n"
    history_existed = history.exists()
    history.mkdir(exist_ok=True)
    done = []
    try:
        write_atomic(task_file, _with_status(task_md, status))
        done.append("task")
        os.rename(bundle, history / task_id)
        done.append("moved")
        if next_live != live_index:
            write_atomic(live_index_file, next_live)
            done.append("live")
        write_atomic(hist_index_file, next_hist)
    except Exception:
        if "live" in done:
            write_atomic(live_index_file, live_index)
        if "moved" in done:
            os.rename(history / task_id, bundle)
        if "task" in done:
            write_atomic(task_file, task_md)
        if not history_existed:
            try:
                history.rmdir()
            except OSError:
                pass
        raise
    return {"taskId": task_id, "status": status, "taskPath": hist_path}


def live_tasks(root):
    ledger = Path(root) / ".ledger"
    tasks = []
    if not ledger.is_dir():
        return tasks
    for entry in sorted(ledger.iterdir()):
        if entry.is_dir() and TASK_ID.match(entry.name) and (entry / "task.md").is_file():
            md = (entry / "task.md").read_text()
            status = re.search(r"^Status:\s+(\S+)", md, re.M)
            tasks.append(
                {
                    "taskId": entry.name,
                    "status": status.group(1) if status else "unknown",
                    "title": _title_from(md, entry.name),
                    "taskPath": f".ledger/{entry.name}/task.md",
                }
            )
    return tasks
