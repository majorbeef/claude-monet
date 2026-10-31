"""Tests for the session notebook and monet-notebook."""
import unittest

from helpers import ROOT, TempDirTest, run

import notebook


class NotebookTest(TempDirTest):
    def test_add_supersede_retire_fold(self):
        a = notebook.add_learning("s1", "  first   learning ")
        b = notebook.add_learning("s1", "second")
        c = notebook.add_learning("s1", "first, corrected", supersedes=[a])
        self.assertEqual([l["id"] for l in notebook.open_learnings("s1")], [b, c])
        notebook.retire_learnings("s1", [b], reason="LEARNINGS.md")
        self.assertEqual([l["content"] for l in notebook.open_learnings("s1")], ["first, corrected"])
        with self.assertRaises(notebook.NotebookError):
            notebook.retire_learnings("s1", [b])
        with self.assertRaises(notebook.NotebookError):
            notebook.add_learning("s1", "x", supersedes=["000000000000"])

    def test_sessions_are_separate_and_torn_lines_skipped(self):
        notebook.add_learning("s1", "one")
        with open(notebook.notebook_path("s1"), "a") as f:
            f.write('{"op": "add", "id": "abc')
        self.assertEqual(len(notebook.open_learnings("s1")), 1)
        self.assertEqual(notebook.open_learnings("s2"), [])

    def test_rejects_unsafe_session_id(self):
        with self.assertRaises(notebook.NotebookError):
            notebook.session_id("../etc")

    def test_cli(self):
        env = {"MONET_NOTEBOOK_DIR": str(self.notebooks), "MONET_SESSION_ID": "cli"}
        out = run([str(ROOT / "bin/monet-notebook"), "add", "use uv, not pip"], self.dir, env)
        self.assertEqual(out.returncode, 0, out.stderr)
        lid = out.stdout.split("[")[1].split("]")[0]
        listed = run([str(ROOT / "bin/monet-notebook"), "list"], self.dir, env)
        self.assertIn(f"[{lid}] use uv, not pip", listed.stdout)
        missing = run([str(ROOT / "bin/monet-notebook"), "list"], self.dir, {"MONET_SESSION_ID": ""})
        self.assertEqual(missing.returncode, 1)
        self.assertIn("MONET_SESSION_ID", missing.stderr)


if __name__ == "__main__":
    unittest.main()
