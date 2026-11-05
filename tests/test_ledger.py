"""Tests for the ledger and monet-ledger."""
import json
import unittest

from helpers import ROOT, TempDirTest, run

import ledger
import notebook


class LedgerTest(TempDirTest):
    def test_add_move_archive(self):
        t = ledger.add_task(self.dir, "Make the thing", "A one-line summary")
        self.assertRegex(t["taskId"], r"^\d{12}-make-the-thing$")
        bundle = self.dir / t["bundlePath"]
        self.assertTrue((bundle / "retrospective.md").exists())
        index = (self.dir / ".ledger/INDEX.md").read_text()
        self.assertIn(f"- `{t['taskPath']}` — planning — Make the thing — A one-line summary", index)

        ledger.set_status(self.dir, t["taskId"], "in-progress")
        self.assertIn("Status: in-progress", (bundle / "task.md").read_text())
        self.assertIn("— in-progress — Make the thing — A one-line summary", (self.dir / ".ledger/INDEX.md").read_text())

        r = ledger.set_status(self.dir, t["bundlePath"] + "/task.md", "done")
        self.assertFalse(bundle.exists())
        hist = self.dir / ".ledger/history" / t["taskId"]
        self.assertIn("Status: done", (hist / "task.md").read_text())
        self.assertNotIn(t["taskId"], (self.dir / ".ledger/INDEX.md").read_text())
        self.assertIn(f"- `{r['taskPath']}` — done — Make the thing — A one-line summary",
                      (self.dir / ".ledger/history/INDEX.md").read_text())
        with self.assertRaises(ledger.LedgerError):
            ledger.set_status(self.dir, t["taskId"], "ready")

    def test_never_committed(self):
        import subprocess
        subprocess.run(["git", "init", "-q", str(self.dir)], check=True)
        t = ledger.add_task(self.dir, "Local only", "Stays out of git")
        status = subprocess.run(["git", "status", "--porcelain", "--untracked-files=all"], cwd=self.dir,
                                capture_output=True, text=True, check=True).stdout
        self.assertEqual(status, "")
        # A ledger made before the rule gets its .gitignore on the next status change.
        (self.dir / ".ledger/.gitignore").unlink()
        ledger.set_status(self.dir, t["taskId"], "ready")
        self.assertTrue((self.dir / ".ledger/.gitignore").exists())

    def test_validation(self):
        with self.assertRaises(ledger.LedgerError):
            ledger.add_task(self.dir, "", "x")
        with self.assertRaises(ledger.LedgerError):
            ledger.add_task(self.dir, "ok", "two\nlines")
        with self.assertRaises(ledger.LedgerError):
            ledger.set_status(self.dir, "not-an-id", "done")
        self.assertEqual(ledger.slug_from("Café: Ünicode & Stuff!"), "cafe-unicode-stuff")

    def test_find_root_prefers_existing_ledger(self):
        (self.dir / ".ledger").mkdir()
        sub = self.dir / "a" / "b"
        sub.mkdir(parents=True)
        self.assertEqual(ledger.find_root(sub), self.dir)

    def test_cli_close_waits_for_distillation(self):
        env = {"MONET_NOTEBOOK_DIR": str(self.notebooks), "MONET_SESSION_ID": "s9"}
        ledger = str(ROOT / "bin/monet-ledger")
        out = run([ledger, "--json", "add", "--title", "Close me", "--description", "d"], self.dir, env)
        self.assertEqual(out.returncode, 0, out.stderr)
        task_id = json.loads(out.stdout)["taskId"]
        notebook.add_learning("s9", "a lesson")
        blocked = run([ledger, "status", task_id, "done"], self.dir, env)
        self.assertEqual(blocked.returncode, 3)
        self.assertIn("a lesson", blocked.stderr)
        closed = run([ledger, "status", task_id, "done", "--learnings-distilled"], self.dir, env)
        self.assertEqual(closed.returncode, 0, closed.stderr)
        self.assertIn("Archived", closed.stdout)


if __name__ == "__main__":
    unittest.main()
