"""Tests for init and log commands."""

import argparse
import tempfile
import unittest
from pathlib import Path

from mdfs.__main__ import cmd_init, cmd_log


class TestInit(unittest.TestCase):

    def test_creates_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_init(argparse.Namespace(dir=tmpdir))
            mdfs = Path(tmpdir) / ".mdfs"
            self.assertTrue((mdfs / "rules").is_dir())
            self.assertTrue((mdfs / "contexts").is_dir())
            self.assertTrue((mdfs / "responses").is_dir())
            self.assertTrue((mdfs / ".gitignore").is_file())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_init(argparse.Namespace(dir=tmpdir))
            cmd_init(argparse.Namespace(dir=tmpdir))
            self.assertTrue((Path(tmpdir) / ".mdfs" / "rules").is_dir())


class TestLog(unittest.TestCase):

    def test_empty_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_init(argparse.Namespace(dir=tmpdir))
            cmd_log(argparse.Namespace(dir=tmpdir))

    def test_log_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd_init(argparse.Namespace(dir=tmpdir))
            ctx = Path(tmpdir) / ".mdfs" / "contexts" / "2025-01-15_120000__test.md"
            ctx.write_text("test", encoding="utf-8")
            resp = Path(tmpdir) / ".mdfs" / "responses" / "2025-01-15_123000__test.md"
            resp.write_text("test", encoding="utf-8")
            cmd_log(argparse.Namespace(dir=tmpdir))


if __name__ == "__main__":
    unittest.main()
