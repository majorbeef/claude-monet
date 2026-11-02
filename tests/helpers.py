"""Shared setup for the monet tests."""
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "lib"))
sys.path.insert(0, str(ROOT / "hooks"))


def run(cmd, cwd, env=None, stdin=None):
    return subprocess.run(
        cmd, cwd=cwd, env={**os.environ, **(env or {})}, input=stdin, capture_output=True, text=True
    )


class TempDirTest(unittest.TestCase):
    """A temporary directory, with notebooks stored inside it and session id s1."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self.tmp.name).resolve()
        self.notebooks = self.dir / "notebooks"
        self.env = mock.patch.dict(os.environ, {"MONET_NOTEBOOK_DIR": str(self.notebooks), "MONET_SESSION_ID": "s1"})
        self.env.start()

    def tearDown(self):
        self.env.stop()
        self.tmp.cleanup()
