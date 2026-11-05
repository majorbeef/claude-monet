"""Tests for monet-review. Run: python3 -m unittest discover -s tests"""
import json
import subprocess
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path

from helpers import TempDirTest, ROOT

import review

DOC = """---
title: x
---
# Session storage

Sessions are stored in SQLite.
They expire after **30 days**.

- one
- two

  continued item
- three

```python
print("hi")

print("there")
```

| a | b |
|---|---|
| 1 | 2 |

> [!NOTE]
> Keep this short.

```mermaid
graph TD; A-->B
```

See [the docs][docs].

[docs]: https://example.com
"""


class SplitTest(unittest.TestCase):
    def test_blocks_and_lines(self):
        blocks = review.split_blocks(DOC)
        kinds = [(b["kind"], b["line"], b["endLine"]) for b in blocks]
        self.assertEqual(kinds, [
            ("frontmatter", 1, 3), ("heading", 4, 4), ("paragraph", 6, 7), ("list", 9, 13), ("code", 15, 19),
            ("table", 21, 23), ("quote", 25, 26), ("mermaid", 28, 30), ("paragraph", 32, 32), ("refs", 34, 34),
        ])
        self.assertEqual(blocks[1]["heading"], {"depth": 1, "text": "Session storage"})
        self.assertIn('print("there")', blocks[4]["raw"])
        self.assertEqual(review.reference_definitions(blocks), "[docs]: https://example.com")

    def test_every_source_line_belongs_to_at_most_one_block(self):
        blocks = review.split_blocks(DOC)
        lines = DOC.split("\n")
        for b in blocks:
            self.assertEqual(b["raw"], "\n".join(lines[b["line"] - 1 : b["endLine"]]))
        for a, b in zip(blocks, blocks[1:]):
            self.assertLess(a["endLine"], b["line"])

    def test_unclosed_fence_runs_to_end(self):
        blocks = review.split_blocks("text\n\n```\ncode\nmore")
        self.assertEqual((blocks[-1]["kind"], blocks[-1]["line"], blocks[-1]["endLine"]), ("code", 3, 5))


class ResultTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "spec.md"
        self.file.write_text(DOC)
        self.page = review.build_page(str(self.file), note="Check the expiry")

    def tearDown(self):
        self.tmp.cleanup()

    def test_page(self):
        self.assertEqual(self.page["title"], "Session storage")
        self.assertTrue(self.page["mermaid"])
        html = review.render_html(self.page, "tok")
        self.assertIn('"token": "tok"', html)
        self.assertNotIn("/*__PAGE_DATA__*/", html)
        self.assertIn("marked v12.0.2", html)
        self.assertIn("mermaid@10.9.1", html)

    def test_script_cannot_escape_page_data(self):
        self.file.write_text("# </script><script>alert(1)</script>\n")
        html = review.render_html(review.build_page(str(self.file)), "tok")
        data = html.split("const PAGE = ", 1)[1].split(";\n", 1)[0]
        self.assertNotIn("</script>", data)

    def test_parse_and_format(self):
        body = {
            "verdict": "approve_notes",
            "overall": "  Mostly good. ",
            "annotations": [
                {"type": "comment", "spans": [{"block": "b3", "start": 0, "end": 10}], "quote": "They expire after 30 days",
                 "text": "Why 30?"},
                {"type": "suggest", "spans": [{"block": "b3", "start": 0, "end": 5}], "quote": "Sessions", "replacement": "Logins"},
                {"type": "label", "label": "good", "spans": [{"block": "b5"}]},
                {"type": "delete", "spans": [{"block": "b3", "start": 0, "end": 3}, {"block": "b4", "start": 0, "end": 3}],
                 "quote": "stored\none"},
            ],
            "edits": [{"block": "b2", "after": "# Login storage"}],
        }
        result = review.parse_result(body, self.page)
        self.assertEqual(result["overall"], "Mostly good.")
        text = review.format_result(result, self.page).replace(self.page["path"], "spec.md")
        self.assertIn("Verdict: Approved with notes", text)
        self.assertIn("## Questions (1)\n\n1. Comment at spec.md:7\n> They expire after 30 days\nNote: Why 30?", text)
        self.assertIn("## Changes and notes (3)\n\n2. Suggested rewrite at spec.md:6", text)
        self.assertIn("The reviewer asked questions.", text)
        self.assertIn("Replace with:\n```\nLogins\n```", text)
        self.assertIn("3. Looks good (whole block) at spec.md:15-19", text)
        self.assertIn("4. Delete at spec.md:6-13", text)
        self.assertIn("### spec.md:4\nBefore:\n````markdown\n# Session storage\n````\nAfter:\n````markdown\n# Login storage", text)

    def test_questions_come_first(self):
        def fmt(body):
            return review.format_result(review.parse_result(body, self.page), self.page).replace(self.page["path"], "spec.md")

        text = fmt({"verdict": "changes", "annotations": [
            {"type": "comment", "spans": [{"block": "b3"}], "text": "Use 60 days."},
            {"type": "label", "label": "clarify", "spans": [{"block": "b5"}]},
            {"type": "comment", "spans": [{"block": "b4"}], "text": "Is this per user? Or global"},
        ]})
        self.assertIn("## Questions (2)\n\n1. Clarify this (whole block)", text)
        self.assertIn("\n2. Comment (whole block) at spec.md:", text)
        self.assertIn("## Changes and notes (1)\n\n3. Comment (whole block) at spec.md:6-7\nNote: Use 60 days.", text)
        self.assertIn("wait for the reviewer's reply", text)

        # Only statements: no questions section, no questions note. A "?" inside a word doesn't count.
        text = fmt({"verdict": "changes", "annotations": [
            {"type": "comment", "spans": [{"block": "b3"}], "text": "See /search?q=x for the format."}]})
        self.assertNotIn("## Questions", text)
        self.assertNotIn("asked questions", text)

        # A question in the overall comment also holds edits back.
        self.assertIn("asked questions", fmt({"verdict": "changes", "overall": "Why not Redis?"}))

    def test_rejects_malformed(self):
        bad = [
            {"verdict": "maybe", "annotations": [], "edits": []},
            {"verdict": "approve", "annotations": [{"type": "comment", "spans": [{"block": "b99"}]}]},
            {"verdict": "approve", "annotations": [{"type": "comment", "spans": [{"block": "b2", "start": 5, "end": 5}]}]},
            {"verdict": "approve", "annotations": [{"type": "suggest", "spans": [{"block": "b2"}]}]},
            {"verdict": "approve", "annotations": [{"type": "label", "label": "meh", "spans": [{"block": "b2"}]}]},
            {"verdict": "approve", "edits": [{"block": "b2"}]},
        ]
        for body in bad:
            with self.assertRaises(review.InvalidResult, msg=body):
                review.parse_result(body, self.page)


class ServerTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.file = Path(self.tmp.name) / "doc.md"
        self.file.write_text("# Title\n\nBody text.\n")

    def tearDown(self):
        self.tmp.cleanup()

    def request(self, url, data=None, headers=None):
        req = urllib.request.Request(url, data=json.dumps(data).encode() if data is not None else None,
                                     headers=headers or {}, method="POST" if data is not None else "GET")
        try:
            with urllib.request.urlopen(req, timeout=5) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as error:
            return error.code, error.read()

    def test_round_trip_through_cli(self):
        proc = subprocess.Popen([sys.executable, str(ROOT / "bin/monet-review"), "doc.md", "--no-open"],
                                cwd=self.tmp.name, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        url = proc.stdout.readline().strip().rsplit(" ", 1)[1]
        base, token = url.split("/?t=")
        self.assertEqual(self.request(base + "/?t=wrong")[0], 404)
        status, html = self.request(url)
        self.assertEqual(status, 200)
        self.assertIn(b"Body text.", html)
        body = {"verdict": "changes", "annotations": [{"type": "comment", "spans": [{"block": "b2"}], "text": "Expand"}], "edits": []}
        self.assertEqual(self.request(base + "/submit", body, {"X-Review-Token": "nope"})[0], 403)
        self.assertEqual(self.request(base + "/submit", {"verdict": "x"}, {"X-Review-Token": token})[0], 400)
        self.assertEqual(self.request(base + "/submit", body, {"X-Review-Token": token})[0], 200)
        out, _ = proc.communicate(timeout=10)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Verdict: Changes requested", out)
        self.assertIn("Comment (whole block) at doc.md:3\nNote: Expand", out)

    def test_rejects_foreign_host(self):
        server = review.ReviewServer(review.build_page(str(self.file)))
        threading.Thread(target=server.serve_until_done, args=(5,), daemon=True).start()
        time.sleep(0.1)
        base, token = server.url.split("/?t=")
        status, _ = self.request(server.url, headers={"Host": "evil.example"})
        self.assertEqual(status, 403)
        server.done.set()

    def test_timeout(self):
        out = subprocess.run([sys.executable, str(ROOT / "bin/monet-review"), str(self.file), "--no-open", "--timeout", "0.3"],
                             capture_output=True, text=True, timeout=10)
        self.assertEqual(out.returncode, 2)


if __name__ == "__main__":
    unittest.main()


class ScratchTest(TempDirTest):
    def test_scratch_reviews_stay_out_of_git(self):
        import subprocess
        subprocess.run(["git", "init", "-q", str(self.dir)], check=True)
        doc = self.dir / ".monet/reviews/2026-01-01-plan.md"
        doc.parent.mkdir(parents=True)
        doc.write_text("# Plan\n")
        review.keep_scratch_out_of_git(doc)
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=self.dir,
                                capture_output=True, text=True, check=True).stdout
        self.assertEqual(status, "")
        other = self.dir / "docs/spec.md"
        other.parent.mkdir()
        other.write_text("# Spec\n")
        review.keep_scratch_out_of_git(other)
        self.assertFalse((self.dir / "docs/.gitignore").exists())
