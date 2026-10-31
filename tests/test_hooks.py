"""Tests for the SessionStart and Stop hooks."""
import json
import sys
import unittest

from helpers import ROOT, TempDirTest, run

import notebook
import reflect


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
        notebook.add_learning("sess-1", "the API rate-limits at 10 rps")
        env = {"CLAUDE_PROJECT_DIR": str(project), "CLAUDE_ENV_FILE": str(env_file),
               "MONET_NOTEBOOK_DIR": str(self.notebooks)}
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


if __name__ == "__main__":
    unittest.main()
