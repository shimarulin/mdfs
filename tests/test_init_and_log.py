"""Tests for init and log commands."""

import argparse
import tempfile
import unittest
from pathlib import Path

from mdfs.commands import InitCommand, LogCommand


class TestInit(unittest.TestCase):

    def test_creates_structure(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            cmd.execute()
            mdfs = Path(tmpdir) / ".mdfs"
            self.assertTrue((mdfs / "rules").is_dir())
            self.assertTrue((mdfs / "contexts").is_dir())
            self.assertTrue((mdfs / "responses").is_dir())
            self.assertTrue((mdfs / ".gitignore").is_file())

    def test_idempotent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            cmd.execute()
            cmd.execute()
            self.assertTrue((Path(tmpdir) / ".mdfs" / "rules").is_dir())


class TestLog(unittest.TestCase):

    def test_empty_log(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            log_cmd.execute()

    def test_log_with_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            ctx = Path(tmpdir) / ".mdfs" / "contexts" / "2025-01-15_120000__test.md"
            ctx.write_text("test", encoding="utf-8")
            resp = Path(tmpdir) / ".mdfs" / "responses" / "2025-01-15_123000__test.md"
            resp.write_text("test", encoding="utf-8")
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            log_cmd.execute()

    def test_log_with_many_files(self):
        """Test log command with multiple files in both directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            
            # Create multiple context files
            contexts_dir = Path(tmpdir) / ".mdfs" / "contexts"
            for i in range(3):
                ctx = contexts_dir / f"2025-01-15_12000{i}__context{i}.md"
                ctx.write_text(f"context {i}", encoding="utf-8")
            
            # Create multiple response files
            responses_dir = Path(tmpdir) / ".mdfs" / "responses"
            for i in range(3):
                resp = responses_dir / f"2025-01-15_13000{i}__response{i}.md"
                resp.write_text(f"response {i}", encoding="utf-8")
            
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            result = log_cmd.execute()
            self.assertEqual(result, 0)

    def test_log_with_only_contexts(self):
        """Test log command with only context files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            
            ctx = Path(tmpdir) / ".mdfs" / "contexts" / "2025-01-15_120000__test.md"
            ctx.write_text("test context", encoding="utf-8")
            
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            result = log_cmd.execute()
            self.assertEqual(result, 0)

    def test_log_with_only_responses(self):
        """Test log command with only response files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            
            resp = Path(tmpdir) / ".mdfs" / "responses" / "2025-01-15_120000__test.md"
            resp.write_text("test response", encoding="utf-8")
            
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            result = log_cmd.execute()
            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
