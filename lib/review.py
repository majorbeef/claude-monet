"""Markdown document review in the browser.

The server splits a Markdown file into top-level blocks with their source lines,
serves one self-contained page on 127.0.0.1 behind a random token, and waits for
the reviewer to finish. The page sends back a verdict, an overall comment,
annotations on text or whole blocks, and rewritten blocks; this module checks
them against the blocks it served and formats them for Claude with path:line
anchors. The file itself is never changed.
"""
import datetime
import html
import json
import re
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

WEB = Path(__file__).resolve().parent / "web"
DATA_MARKER = "/*__PAGE_DATA__*/null"
VENDOR_MARKER = "<!--__VENDOR__-->"
MERMAID_URL = "https://cdn.jsdelivr.net/npm/mermaid@10.9.1/dist/mermaid.min.js"

TYPES = {"comment", "delete", "suggest", "label"}
LABELS = {"good": "Looks good", "clarify": "Clarify this"}
VERDICTS = {
    "approve": "Approved",
    "approve_notes": "Approved with notes",
    "changes": "Changes requested",
    "dismissed": "Dismissed without a verdict",
}
TYPE_TEXT = {"comment": "Comment", "delete": "Delete", "suggest": "Suggested rewrite", "label": "Label"}

# ---------------------------------------------------------------------------
# Blocks

FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})(.*)$")
HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+(.*?))?[ \t#]*$")
LIST_ITEM = re.compile(r"^ {0,3}(?:[-*+]|\d{1,9}[.)])(?:[ \t]|$)")
REF_DEF = re.compile(r"^ {0,3}\[[^\]]+\]:\s*\S+")


def split_blocks(source):
    """Top-level Markdown blocks: [{id, raw, line, endLine, kind, heading?, lang?}].

    A block is a fenced code block, an ATX heading, YAML front matter, or a run of
    non-blank lines. A list continues across blank lines while the next line is
    indented or another item, so a loose list stays one block.
    """
    lines = source.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    blocks = []

    def add(start, end, kind, **extra):
        raw = "\n".join(lines[start : end + 1])
        blocks.append(dict(id=f"b{len(blocks) + 1}", raw=raw, line=start + 1, endLine=end + 1, kind=kind, **extra))

    i = 0
    n = len(lines)
    if n and lines[0].strip() == "---":
        for j in range(1, n):
            if lines[j].strip() in ("---", "..."):
                add(0, j, "frontmatter")
                i = j + 1
                break
    while i < n:
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        fence = FENCE.match(line)
        if fence:
            marker = fence.group(1)
            lang = fence.group(2).strip().split(" ")[0].lower() if fence.group(2).strip() else ""
            j = i + 1
            while j < n and not re.match(rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}\s*$", lines[j]):
                j += 1
            end = min(j, n - 1)
            add(i, end, "mermaid" if lang == "mermaid" else "code", lang=lang)
            i = end + 1
            continue
        heading = HEADING.match(line)
        if heading:
            add(i, i, "heading", heading={"depth": len(heading.group(1)), "text": (heading.group(2) or "").strip()})
            i += 1
            continue
        start = i
        is_list = bool(LIST_ITEM.match(line))
        j = i
        while True:
            while j + 1 < n and lines[j + 1].strip() and not FENCE.match(lines[j + 1]) and not HEADING.match(lines[j + 1]):
                j += 1
            if not is_list:
                break
            k = j + 1
            while k < n and not lines[k].strip():
                k += 1
            if k < n and (lines[k].startswith(("  ", "\t")) or LIST_ITEM.match(lines[k])):
                j = k
                continue
            break
        kind = "list" if is_list else "table" if line.lstrip().startswith("|") else "quote" if line.lstrip().startswith(">") else "paragraph"
        if all(REF_DEF.match(l) for l in lines[start : j + 1]):
            kind = "refs"
        add(start, j, kind)
        i = j + 1
    return blocks


def reference_definitions(blocks):
    """Link reference definitions, appended when each block renders on its own."""
    return "\n".join(b["raw"] for b in blocks if b["kind"] == "refs")


def git_root(path):
    proc = subprocess.run(
        ["git", "rev-parse", "--show-toplevel"], cwd=path.parent, capture_output=True, text=True
    )
    return Path(proc.stdout.strip()).resolve() if proc.returncode == 0 and proc.stdout.strip() else None


def build_page(path, note=None, cwd=None):
    file = Path(path)
    if not file.is_absolute():
        file = Path(cwd or ".").resolve() / file
    file = file.resolve()
    source = file.read_text(encoding="utf-8")
    blocks = split_blocks(source)
    root = git_root(file) or Path(cwd or ".").resolve()
    try:
        shown = str(file.relative_to(root))
    except ValueError:
        shown = str(file)
    title = next((b["heading"]["text"] for b in blocks if b.get("heading", {}).get("depth") == 1), file.name)
    return {
        "kind": "markdown-review",
        "title": title,
        "path": shown,
        "absPath": str(file),
        "note": (note or "").strip() or None,
        "createdAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
        "blocks": blocks,
        "refs": reference_definitions(blocks),
        "mermaid": any(b["kind"] == "mermaid" for b in blocks),
    }


def render_html(page, token):
    template = (WEB / "review.html").read_text(encoding="utf-8")
    vendor = "".join(
        f"<script>{(WEB / 'vendor' / name).read_text(encoding='utf-8')}</script>"
        for name in ("marked.min.js", "purify.min.js")
    )
    if page["mermaid"]:
        vendor += f'<script src="{MERMAID_URL}" crossorigin="anonymous"></script>'
    data = json.dumps(dict(page, token=token), ensure_ascii=False)
    data = data.replace("<", "\\u003c").replace(">", "\\u003e").replace("&", "\\u0026")
    data = data.replace("\u2028", "\\u2028").replace("\u2029", "\\u2029")
    # Title first and data last, so text inside the document or libraries is never treated as a marker.
    page_html = template.replace("__TITLE__", html.escape(page["title"]))
    page_html = page_html.replace(VENDOR_MARKER, vendor, 1)
    return page_html.replace(DATA_MARKER, data, 1)

# ---------------------------------------------------------------------------
# What the page sends back


class InvalidResult(ValueError):
    pass


def _spans(value, ids):
    if not isinstance(value, list) or not value:
        raise InvalidResult("an annotation needs at least one span")
    spans = []
    for span in value:
        if not isinstance(span, dict) or span.get("block") not in ids:
            raise InvalidResult("a span names an unknown block")
        start, end = span.get("start"), span.get("end")
        if start is None and end is None:
            spans.append({"block": span["block"]})
        elif isinstance(start, int) and isinstance(end, int) and 0 <= start < end:
            spans.append({"block": span["block"], "start": start, "end": end})
        else:
            raise InvalidResult("a span has an invalid range")
    return spans


def _opt_str(value):
    if value is None:
        return None
    if not isinstance(value, str):
        raise InvalidResult("expected a string")
    return value.strip() or None


def parse_result(body, page):
    """Validate the page's submission against the page served. Anything malformed is rejected whole."""
    if not isinstance(body, dict) or body.get("verdict") not in VERDICTS:
        raise InvalidResult("unknown verdict")
    ids = {b["id"] for b in page["blocks"]}
    annotations = []
    for a in body.get("annotations") or []:
        if not isinstance(a, dict) or a.get("type") not in TYPES:
            raise InvalidResult("unknown annotation type")
        item = {"type": a["type"], "spans": _spans(a.get("spans"), ids), "quote": _opt_str(a.get("quote")),
                "text": _opt_str(a.get("text"))}
        if a["type"] == "suggest":
            if not isinstance(a.get("replacement"), str):
                raise InvalidResult("a suggestion needs replacement text")
            item["replacement"] = a["replacement"]
        if a["type"] == "label":
            if a.get("label") not in LABELS:
                raise InvalidResult("unknown label")
            item["label"] = a["label"]
        annotations.append(item)
    edits = []
    for e in body.get("edits") or []:
        if not isinstance(e, dict) or e.get("block") not in ids or not isinstance(e.get("after"), str):
            raise InvalidResult("invalid block rewrite")
        edits.append({"block": e["block"], "after": e["after"]})
    return {
        "verdict": body["verdict"],
        "overall": _opt_str(body.get("overall")),
        "annotations": annotations,
        "edits": edits,
        "submittedAt": datetime.datetime.now().astimezone().isoformat(timespec="seconds"),
    }

# ---------------------------------------------------------------------------
# Text for Claude


def _first_line(block, quote):
    """The source line a quote starts on, when its first words can be found in the block."""
    if not quote:
        return None
    words = re.findall(r"\w+", quote.split("\n")[0])[:6]
    if not words:
        return None
    pattern = re.compile(r"\W+".join(re.escape(w) for w in words))
    for offset, text in enumerate(block["raw"].split("\n")):
        if pattern.search(text):
            return block["line"] + offset
    return None


def anchor(page, spans, quote=None):
    """`path:30` or `path:30-34` for the lines an annotation touches."""
    blocks = [b for b in page["blocks"] if any(s["block"] == b["id"] for s in spans)]
    start = min(b["line"] for b in blocks)
    end = max(b["endLine"] for b in blocks)
    whole = all("start" not in s for s in spans)
    if not whole and len(blocks) == 1 and quote:
        first = _first_line(blocks[0], quote)
        if first:
            start = first
            end = min(end, first + quote.count("\n"))
    return f"{page['path']}:{start}" + (f"-{end}" if end > start else "")


def _quote_md(text):
    return "\n".join("> " + l if l else ">" for l in text.split("\n"))


def asks_question(text):
    """True when the text contains a question: a `?` that ends a sentence."""
    return bool(text) and re.search(r"\?(\s|$)", text) is not None


def is_question(annotation):
    """A ❓ label, or a note that asks something. The reviewer wants an answer, not an edit."""
    if annotation["type"] == "label":
        return annotation.get("label") == "clarify"
    return annotation["type"] == "comment" and asks_question(annotation.get("text"))


QUESTIONS_FIRST = (
    "Answer each question in the conversation, then stop and wait for the reviewer's reply. "
    "Don't pick an answer yourself and don't edit the parts a question covers until they've replied. "
    "You may apply the changes that no question touches now."
)


def keep_scratch_out_of_git(path):
    """Documents written for review go in .monet/reviews/; a `*` .gitignore keeps .monet/ out of git."""
    parts = Path(path).resolve().parts
    if ".monet" not in parts:
        return
    root = Path(*parts[: parts.index(".monet") + 1])
    ignore = root / ".gitignore"
    if not ignore.exists():
        ignore.write_text("# monet scratch files: never committed.\n*\n")


def format_result(result, page):
    out = [f"# Document review: {page['path']}", "", f"Verdict: {VERDICTS[result['verdict']]}"]
    if result.get("overall"):
        out += ["", "Overall comment:", result["overall"]]
    # Questions go first, numbered on from 1; changes and notes continue the numbering.
    questions = [a for a in result["annotations"] if is_question(a)]
    others = [a for a in result["annotations"] if not is_question(a)]
    number = 0
    for title, group in (("Questions", questions), ("Changes and notes", others)):
        if not group:
            continue
        out += ["", f"## {title} ({len(group)})"]
        for a in group:
            number += 1
            kind = LABELS[a["label"]] if a["type"] == "label" else TYPE_TEXT[a["type"]]
            whole = all("start" not in s for s in a["spans"])
            out += ["", f"{number}. {kind}{' (whole block)' if whole else ''} at {anchor(page, a['spans'], a.get('quote'))}"]
            if a.get("quote"):
                out.append(_quote_md(a["quote"]))
            if a["type"] == "suggest":
                out += ["Replace with:", "```", a["replacement"], "```"]
            if a.get("text"):
                out.append(f"Note: {a['text']}")
    if result["edits"]:
        by_id = {b["id"]: b for b in page["blocks"]}
        out += ["", f"## Rewritten blocks ({len(result['edits'])})"]
        for e in result["edits"]:
            b = by_id[e["block"]]
            out += ["", f"### {page['path']}:{b['line']}" + (f"-{b['endLine']}" if b["endLine"] > b["line"] else ""),
                    "Before:", "````markdown", b["raw"], "````", "After:", "````markdown", e["after"], "````"]
    if not result["annotations"] and not result["edits"] and not result.get("overall"):
        out += ["", "No annotations."]
    out += ["", "The file was not changed. Apply the feedback yourself; an approval covers only what the reviewer saw."]
    if questions or asks_question(result.get("overall")):
        out += ["", f"The reviewer asked questions. {QUESTIONS_FIRST}"]
    return "\n".join(out)

# ---------------------------------------------------------------------------
# Server


class ReviewServer:
    def __init__(self, page, host="127.0.0.1", port=0):
        self.page = page
        self.token = secrets.token_urlsafe(24)
        self.result = None
        self.done = threading.Event()
        self.html = render_html(page, self.token).encode("utf-8")
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *args):
                pass

            def _host_ok(self):
                host = (self.headers.get("Host") or "").split(":")[0]
                return host in ("127.0.0.1", "localhost")

            def _send(self, code, body, ctype="application/json"):
                data = body if isinstance(body, bytes) else json.dumps(body).encode()
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(data)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.send_header("Referrer-Policy", "no-referrer")
                self.end_headers()
                self.wfile.write(data)

            def do_GET(self):
                url = urlparse(self.path)
                if not self._host_ok():
                    return self._send(403, {"error": "forbidden"})
                if url.path == "/" and parse_qs(url.query).get("t", [""])[0] == server.token:
                    return self._send(200, server.html, "text/html; charset=utf-8")
                if url.path == "/status":
                    return self._send(200, {"live": not server.done.is_set()})
                self._send(404, {"error": "not found"})

            def do_POST(self):
                url = urlparse(self.path)
                if not self._host_ok() or self.headers.get("X-Review-Token") != server.token:
                    return self._send(403, {"error": "forbidden"})
                if url.path != "/submit":
                    return self._send(404, {"error": "not found"})
                if server.done.is_set():
                    return self._send(409, {"error": "This review was already submitted."})
                try:
                    length = int(self.headers.get("Content-Length") or 0)
                    if length > 5_000_000:
                        raise InvalidResult("submission too large")
                    body = json.loads(self.rfile.read(length) or b"null")
                    result = parse_result(body, server.page)
                except (InvalidResult, json.JSONDecodeError, ValueError) as error:
                    return self._send(400, {"error": str(error)})
                server.result = result
                self._send(200, {"ok": True})
                server.done.set()

        self.httpd = ThreadingHTTPServer((host, port), Handler)
        self.httpd.daemon_threads = True
        self.url = f"http://127.0.0.1:{self.httpd.server_address[1]}/?t={self.token}"

    def serve_until_done(self, timeout=None):
        thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        thread.start()
        finished = self.done.wait(timeout)
        self.httpd.shutdown()
        self.httpd.server_close()
        return self.result if finished else None
