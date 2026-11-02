"""Tests for the generated-file guard, the LEARNINGS.md budget note, and the status line."""
import json
import os
import sys
import unittest
from unittest import mock

from helpers import ROOT, TempDirTest, run

import generated_guard


class GeneratedGuardTest(TempDirTest):
    def setUp(self):
        super().setUp()
        big = "x" * 30_000
        for rel in ("package-lock.json", "node_modules/lib/index.d.ts", "node_modules/lib/big.js", "dist/app.min.js",
                    "src/app.ts", "small/yarn.lock"):
            path = self.dir / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(big if rel not in ("node_modules/lib/index.d.ts", "small/yarn.lock") else "small")

    def read(self, path, **extra):
        return generated_guard.decide({"tool_name": "Read", "cwd": str(self.dir),
                                       "tool_input": dict(file_path=path, **extra)})

    def bash(self, command):
        return generated_guard.decide({"tool_name": "Bash", "cwd": str(self.dir), "tool_input": {"command": command}})

    def test_blocks_whole_reads_of_large_generated_files(self):
        for path in ("package-lock.json", "node_modules/lib/big.js", str(self.dir / "dist/app.min.js")):
            out = self.read(path)
            self.assertEqual(out["hookSpecificOutput"]["permissionDecision"], "deny", path)
            self.assertIn("grep -n", out["hookSpecificOutput"]["permissionDecisionReason"])

    def test_allows_small_files_slices_and_source(self):
        self.assertIsNone(self.read("node_modules/lib/index.d.ts"))  # small: useful API types
        self.assertIsNone(self.read("small/yarn.lock"))
        self.assertIsNone(self.read("package-lock.json", offset=1, limit=100))
        self.assertIsNone(self.read("src/app.ts"))
        self.assertIsNone(self.read("does/not/exist/package-lock.json"))

    def test_bash(self):
        self.assertIsNotNone(self.bash("cat package-lock.json"))
        self.assertIsNotNone(self.bash("cd x && less node_modules/lib/big.js"))
        for ok in ("grep -n lodash package-lock.json", "head -50 package-lock.json", "cat package-lock.json | grep x",
                   "jq '.packages | keys' package-lock.json", "cat src/app.ts", "wc -l package-lock.json"):
            self.assertIsNone(self.bash(ok), ok)

    def test_threshold_and_off_switch(self):
        with mock.patch.dict(os.environ, {"MONET_GENERATED_GUARD_BYTES": "100000"}):
            self.assertIsNone(self.read("package-lock.json"))
        event = json.dumps({"tool_name": "Read", "cwd": str(self.dir), "tool_input": {"file_path": "package-lock.json"}})
        hook = [sys.executable, str(ROOT / "hooks/generated_guard.py")]
        self.assertIn('"deny"', run(hook, self.dir, {}, event).stdout)
        self.assertEqual(run(hook, self.dir, {"MONET_GENERATED_GUARD": "0"}, event).stdout, "")


class LearningsBudgetTest(TempDirTest):
    def start(self, learnings):
        project = self.dir / "proj"
        (project / ".claude").mkdir(parents=True, exist_ok=True)
        (project / ".claude/LEARNINGS.md").write_text(learnings)
        out = run([sys.executable, str(ROOT / "hooks/session_start.py")], project,
                  {"CLAUDE_PROJECT_DIR": str(project)}, json.dumps({"session_id": "s1", "source": "startup"}))
        return json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]

    def test_note_only_when_over_budget(self):
        self.assertNotIn("offer to trim", self.start("- Use make check.\n"))
        ctx = self.start("- a long learning line here\n" * 400)
        self.assertIn("offer to trim it under 1,500", ctx)


class StatusLineTest(TempDirTest):
    def line(self, data, *args):
        return run([sys.executable, str(ROOT / "bin/monet-statusline"), "--no-color", *args], self.dir, {},
                   json.dumps(data)).stdout.strip()

    def test_render(self):
        data = {"model": {"display_name": "Opus"}, "cost": {"total_cost_usd": 1.234},
                "context_window": {"used_percentage": 82.4, "current_usage": {
                    "input_tokens": 100, "cache_creation_input_tokens": 400, "cache_read_input_tokens": 4500}}}
        self.assertEqual(self.line(data), "Opus · ▓▓▓▓▓▓▓▓░░ 82% ctx /compact? · cache 90% · $1.23")
        self.assertEqual(self.line({}), "Claude")
        self.assertEqual(self.line({"context_window": {"used_percentage": None, "current_usage": None}}), "Claude")

    def test_install_keeps_other_settings_and_existing_status_line(self):
        home = self.dir / "home"
        home.mkdir()
        (home / "settings.json").write_text(json.dumps({"model": "opus", "statusLine": {"type": "command", "command": "mine"}}))
        cmd = [sys.executable, str(ROOT / "bin/monet-statusline"), "--install"]
        refused = run(cmd, self.dir, {"CLAUDE_CONFIG_DIR": str(home)})
        self.assertEqual(refused.returncode, 1)
        self.assertEqual(json.loads((home / "settings.json").read_text())["statusLine"]["command"], "mine")
        forced = run(cmd + ["--force"], self.dir, {"CLAUDE_CONFIG_DIR": str(home)})
        self.assertEqual(forced.returncode, 0, forced.stderr)
        settings = json.loads((home / "settings.json").read_text())
        self.assertEqual(settings["model"], "opus")
        self.assertTrue(settings["statusLine"]["command"].endswith("monet/statusline.py"))
        self.assertTrue((home / "monet/statusline.py").exists())
        self.assertTrue((home / "settings.json.bak").exists())


if __name__ == "__main__":
    unittest.main()
