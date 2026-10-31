"""Tests for the monet plugin's CLIs and hooks. Run: python3 -m unittest discover -s tests"""
import io
import json
import os
import subprocess
import sys
import tempfile
import textwrap
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "hooks"))

import monet  # noqa: E402
import reflect  # noqa: E402
import rtk_rewrite  # noqa: E402


def run(cmd, cwd, env=None, stdin=None):
    return subprocess.run(
        cmd, cwd=cwd, env={**os.environ, **(env or {})}, input=stdin, capture_output=True, text=True
    )


class TempDirTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name).resolve()
        self.notebooks = self.dir / "notebooks"
        self.env = mock.patch.dict(os.environ, {"MONET_NOTEBOOK_DIR": str(self.notebooks), "MONET_SESSION_ID": "s1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()


class NotebookTest(TempDirTest):
    def test_add_supersede_retire_fold(self):
        a = monet.add_learning("s1", "  first   learning ")
        b = monet.add_learning("s1", "second")
        c = monet.add_learning("s1", "first, corrected", supersedes=[a])
        self.assertEqual([l["id"] for l in monet.open_learnings("s1")], [b, c])
        monet.retire_learnings("s1", [b], reason="LEARNINGS.md")
        self.assertEqual([l["content"] for l in monet.open_learnings("s1")], ["first, corrected"])
        with self.assertRaises(monet.NotebookError):
            monet.retire_learnings("s1", [b])
        with self.assertRaises(monet.NotebookError):
            monet.add_learning("s1", "x", supersedes=["000000000000"])

    def test_sessions_are_separate_and_torn_lines_skipped(self):
        monet.add_learning("s1", "one")
        with open(monet.notebook_path("s1"), "a") as f:
            f.write('{"op": "add", "id": "abc')
        self.assertEqual(len(monet.open_learnings("s1")), 1)
        self.assertEqual(monet.open_learnings("s2"), [])

    def test_rejects_unsafe_session_id(self):
        with self.assertRaises(monet.NotebookError):
            monet.session_id("../etc")

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


class LedgerTest(TempDirTest):
    def test_add_move_archive(self):
        t = monet.add_task(self.dir, "Make the thing", "A one-line summary")
        self.assertRegex(t["taskId"], r"^\d{12}-make-the-thing$")
        bundle = self.dir / t["bundlePath"]
        self.assertTrue((bundle / "retrospective.md").exists())
        index = (self.dir / ".ledger/INDEX.md").read_text()
        self.assertIn(f"- `{t['taskPath']}` — planning — Make the thing — A one-line summary", index)

        monet.set_status(self.dir, t["taskId"], "in-progress")
        self.assertIn("Status: in-progress", (bundle / "task.md").read_text())
        self.assertIn("— in-progress — Make the thing — A one-line summary", (self.dir / ".ledger/INDEX.md").read_text())

        r = monet.set_status(self.dir, t["bundlePath"] + "/task.md", "done")
        self.assertFalse(bundle.exists())
        hist = self.dir / ".ledger/history" / t["taskId"]
        self.assertIn("Status: done", (hist / "task.md").read_text())
        self.assertNotIn(t["taskId"], (self.dir / ".ledger/INDEX.md").read_text())
        self.assertIn(f"- `{r['taskPath']}` — done — Make the thing — A one-line summary",
                      (self.dir / ".ledger/history/INDEX.md").read_text())
        with self.assertRaises(monet.LedgerError):
            monet.set_status(self.dir, t["taskId"], "ready")

    def test_validation(self):
        with self.assertRaises(monet.LedgerError):
            monet.add_task(self.dir, "", "x")
        with self.assertRaises(monet.LedgerError):
            monet.add_task(self.dir, "ok", "two\nlines")
        with self.assertRaises(monet.LedgerError):
            monet.set_status(self.dir, "not-an-id", "done")
        self.assertEqual(monet.slug_from("Café: Ünicode & Stuff!"), "cafe-unicode-stuff")

    def test_find_root_prefers_existing_ledger(self):
        (self.dir / ".ledger").mkdir()
        sub = self.dir / "a" / "b"
        sub.mkdir(parents=True)
        self.assertEqual(monet.find_root(sub), self.dir)

    def test_cli_close_waits_for_distillation(self):
        env = {"MONET_NOTEBOOK_DIR": str(self.notebooks), "MONET_SESSION_ID": "s9"}
        ledger = str(ROOT / "bin/monet-ledger")
        out = run([ledger, "--json", "add", "--title", "Close me", "--description", "d"], self.dir, env)
        self.assertEqual(out.returncode, 0, out.stderr)
        task_id = json.loads(out.stdout)["taskId"]
        monet.add_learning("s9", "a lesson")
        blocked = run([ledger, "status", task_id, "done"], self.dir, env)
        self.assertEqual(blocked.returncode, 3)
        self.assertIn("a lesson", blocked.stderr)
        closed = run([ledger, "status", task_id, "done", "--learnings-distilled"], self.dir, env)
        self.assertEqual(closed.returncode, 0, closed.stderr)
        self.assertIn("Archived", closed.stdout)


class RtkTest(unittest.TestCase):
    def fake(self, code, stdout):
        return lambda *a, **k: subprocess.CompletedProcess(a[0], code, stdout=stdout, stderr="")

    def event(self, command):
        return {"tool_name": "Bash", "tool_input": {"command": command, "description": "d"}}

    def test_allow_rewrites_and_approves(self):
        out = rtk_rewrite.decide(self.event("git status"), run=self.fake(0, "rtk git status\n"))
        hso = out["hookSpecificOutput"]
        self.assertEqual(hso["permissionDecision"], "allow")
        self.assertEqual(hso["updatedInput"], {"command": "rtk git status", "description": "d"})

    def test_ask_rewrites_without_decision(self):
        out = rtk_rewrite.decide(self.event("cargo test"), run=self.fake(3, "rtk cargo test"))
        self.assertNotIn("permissionDecision", out["hookSpecificOutput"])

    def test_pass_through_cases(self):
        for code, stdout, cmd in [
            (1, "", "ls"),
            (2, "rtk rm -rf x", "rm -rf x"),
            (0, "git diff", "git diff"),
            (0, "rtk git diff", "git diff  # verbatim"),
            (0, "rtk cat", "cat <<EOF\nx\nEOF"),
            (0, "rtk rtk ls", "rtk ls"),
        ]:
            self.assertIsNone(rtk_rewrite.decide(self.event(cmd), run=self.fake(code, stdout)), cmd)


class ReflectTest(TempDirTest):
    def write_transcript(self, entries):
        path = self.dir / "t.jsonl"
        with open(path, "a") as f:
            for e in entries:
                f.write(json.dumps(e) + "\n")
        return path

    def assistant(self, mid, tokens, tool=None):
        content = [{"type": "text", "text": "hi"}]
        if tool:
            content.append({"type": "tool_use", "id": tool[0], "name": "Bash", "input": {"command": tool[1]}})
        return {"type": "assistant", "message": {"id": mid, "content": content,
                "usage": {"input_tokens": tokens, "cache_creation_input_tokens": 0, "cache_read_input_tokens": 999999,
                          "output_tokens": 0}}}

    def test_blocks_once_after_spacing_with_evidence(self):
        path = self.write_transcript([
            self.assistant("m1", 60, tool=("t1", "pytest -x")),
            self.assistant("m1", 60),  # same message split across entries counts once
            {"type": "user", "message": {"content": [{"type": "tool_result", "tool_use_id": "t1", "is_error": True}]}},
        ])
        event = {"transcript_path": str(path), "session_id": "s1"}
        out, state = reflect.decide(event, {}, spacing=100)
        self.assertIsNone(out)
        self.assertEqual(state["tokens"], 60)
        self.write_transcript([self.assistant("m2", 50)])
        out, state = reflect.decide(event, state, spacing=100)
        self.assertEqual(out["decision"], "block")
        self.assertIn("Bash: `pytest -x`", out["reason"])
        self.assertEqual(state["tokens"], 0)
        out, state = reflect.decide(event, state, spacing=100)
        self.assertIsNone(out)

    def test_respects_stop_hook_active_and_zero(self):
        path = self.write_transcript([self.assistant("m1", 500)])
        out, _ = reflect.decide({"transcript_path": str(path), "stop_hook_active": True}, {}, spacing=100)
        self.assertIsNone(out)
        out, _ = reflect.decide({"transcript_path": str(path)}, {}, spacing=0)
        self.assertIsNone(out)


class SessionStartTest(TempDirTest):
    def test_context_env_and_compaction_packet(self):
        project = self.dir / "proj"
        (project / ".claude").mkdir(parents=True)
        (project / ".claude/LEARNINGS.md").write_text("- Run tests with `make check`.\n")
        (project / ".ledger").mkdir()
        env_file = self.dir / "env"
        monet.add_learning("sess-1", "the API rate-limits at 10 rps")
        env = {"CLAUDE_PROJECT_DIR": str(project), "CLAUDE_ENV_FILE": str(env_file),
               "MONET_NOTEBOOK_DIR": str(self.notebooks), "MONET_RTK": "0"}
        stdin = json.dumps({"session_id": "sess-1", "source": "compact", "cwd": str(project)})
        out = run([sys.executable, str(ROOT / "hooks/session_start.py")], project, env, stdin)
        ctx = json.loads(out.stdout)["hookSpecificOutput"]["additionalContext"]
        self.assertIn("make check", ctx)
        self.assertIn("monet-ledger add", ctx)
        self.assertIn("the API rate-limits at 10 rps", ctx)
        self.assertIn("export MONET_SESSION_ID=sess-1", env_file.read_text())

        stdin = json.dumps({"session_id": "sess-1", "source": "startup"})
        out = run([sys.executable, str(ROOT / "hooks/session_start.py")], project, env, stdin)
        self.assertNotIn("rate-limits", out.stdout)


class RalphTest(TempDirTest):
    def setUp(self):
        super().setUp()
        self.repo = self.dir / "repo"
        self.repo.mkdir()
        for cmd in (["git", "init", "-q"], ["git", "config", "user.email", "t@t"], ["git", "config", "user.name", "t"]):
            run(cmd, self.repo)
        (self.repo / "a.txt").write_text("a\n")
        run(["git", "add", "."], self.repo)
        run(["git", "commit", "-qm", "init"], self.repo)
        self.fake = self.dir / "fake-claude"
        self.fake.write_text(textwrap.dedent(f"""\
            #!{sys.executable}
            import json, os, sys
            from pathlib import Path
            n = int(os.environ.get("FAKE_LINES", "5"))
            calls = Path(os.environ["FAKE_LOG"])
            calls.write_text(calls.read_text() + json.dumps(sys.argv[1:]) + "\\n" if calls.exists() else json.dumps(sys.argv[1:]) + "\\n")
            i = len(calls.read_text().splitlines())
            with open("work.txt", "a") as f:
                f.write("".join(f"line {{i}}-{{k}}\\n" for k in range(n)))
            if os.environ.get("FAKE_DONE_AT") == str(i):
                task = os.environ["FAKE_TASK"]
                Path(task).write_text(Path(task).read_text().replace("Status: in-progress", "Status: done"))
            print(json.dumps({{"is_error": False, "result": f"did increment {{i}}", "num_turns": 3, "total_cost_usd": 0.01}}))
            """))
        self.fake.chmod(0o755)
        self.log = self.dir / "calls.log"

    def ralph(self, *args, **env):
        base = {"MONET_CLAUDE_BIN": str(self.fake), "FAKE_LOG": str(self.log)}
        base.update({k: str(v) for k, v in env.items()})
        return run([sys.executable, str(ROOT / "bin/monet-ralph"), *args], self.repo, base)

    def test_runs_requested_iterations(self):
        out = self.ralph("--goal", "grow work.txt", "--iterations", "3", "--", "--max-turns", "9")
        self.assertEqual(out.returncode, 0, out.stderr)
        summary = json.loads(out.stdout)
        self.assertEqual(summary["status"], "completed")
        self.assertEqual(summary["completedIterations"], 3)
        argv = json.loads(self.log.read_text().splitlines()[0])
        self.assertIn("grow work.txt", argv[1])
        self.assertEqual(argv[argv.index("--agent") + 1], "monet:implementation-engineer")
        self.assertEqual(argv[-2:], ["--max-turns", "9"])

    def test_low_mutation_stop(self):
        out = self.ralph("--goal", "g", "--iterations", "5", FAKE_LINES=0)
        summary = json.loads(out.stdout)
        self.assertEqual((summary["status"], summary["stopReason"], summary["completedIterations"]),
                         ("stopped", "low-mutation", 3))  # round 1 creates an empty file

    def test_ledger_task_stop_and_log(self):
        t = monet.add_task(self.repo, "Loop task", "d")
        monet.set_status(self.repo, t["taskId"], "in-progress")
        task_md = self.repo / t["taskPath"]
        out = self.ralph("--task", t["taskId"], "--goal", "g", "--iterations", "5",
                         FAKE_DONE_AT=2, FAKE_TASK=task_md)
        summary = json.loads(out.stdout)
        self.assertEqual((summary["status"], summary["stopReason"], summary["completedIterations"]),
                         ("stopped", "task-done", 2))
        self.assertIn("did increment 2", (task_md.parent / "ralph-log.md").read_text())

    def test_failed_worker(self):
        self.fake.write_text(f"#!{sys.executable}\nimport sys\nsys.exit(2)\n")
        out = self.ralph("--goal", "g", "--iterations", "2")
        self.assertEqual(out.returncode, 1)
        self.assertEqual(json.loads(out.stdout)["status"], "failed")


if __name__ == "__main__":
    unittest.main()
