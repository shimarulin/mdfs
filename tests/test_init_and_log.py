"""Tests for init and log commands."""

import argparse
import tempfile
import unittest
from pathlib import Path

from mdfs.commands import InitCommand, LogCommand


class TestInit(unittest.TestCase):

    def test_creates_config(self):
        """Test that init creates .mdfsrc.yaml config file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            cmd.execute()
            config_file = Path(tmpdir) / ".mdfsrc.yaml"
            self.assertTrue(config_file.is_file())

    def test_no_directories_created(self):
        """Test that init does NOT create .mdfs or any subdirectories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            cmd.execute()
            mdfs = Path(tmpdir) / ".mdfs"
            # .mdfs directory should NOT exist
            self.assertFalse(mdfs.is_dir())

    def test_idempotent(self):
        """Test that init can be run multiple times safely."""
        with tempfile.TemporaryDirectory() as tmpdir:
            cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            result1 = cmd.execute()
            result2 = cmd.execute()
            self.assertEqual(result1, 0)
            self.assertEqual(result2, 0)
            # Config file should exist
            config_file = Path(tmpdir) / ".mdfsrc.yaml"
            self.assertTrue(config_file.is_file())


class TestLog(unittest.TestCase):

    def test_empty_log(self):
        """Test log command with no files - should work but find no contexts/responses."""
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            # Create empty .mdfs directory structure so log can find the root
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir(exist_ok=True)
            (mdfs_dir / "contexts").mkdir(exist_ok=True)
            (mdfs_dir / "responses").mkdir(exist_ok=True)
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            result = log_cmd.execute()
            self.assertEqual(result, 0)

    def test_log_with_files(self):
        """Test log command with context and response files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            # Create directories for files
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir(exist_ok=True)
            contexts_dir = mdfs_dir / "contexts"
            responses_dir = mdfs_dir / "responses"
            contexts_dir.mkdir(exist_ok=True)
            responses_dir.mkdir(exist_ok=True)
            
            ctx = contexts_dir / "2025-01-15_120000__test.md"
            ctx.write_text("test", encoding="utf-8")
            resp = responses_dir / "2025-01-15_123000__test.md"
            resp.write_text("test", encoding="utf-8")
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            result = log_cmd.execute()
            self.assertEqual(result, 0)

    def test_log_with_many_files(self):
        """Test log command with multiple files in both directories."""
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            
            # Create directories structure
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir(exist_ok=True)
            contexts_dir = mdfs_dir / "contexts"
            responses_dir = mdfs_dir / "responses"
            contexts_dir.mkdir(exist_ok=True)
            responses_dir.mkdir(exist_ok=True)
            
            # Create multiple context files
            for i in range(3):
                ctx = contexts_dir / f"2025-01-15_12000{i}__context{i}.md"
                ctx.write_text(f"context {i}", encoding="utf-8")
            
            # Create multiple response files
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
            
            # Create directories
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir(exist_ok=True)
            contexts_dir = mdfs_dir / "contexts"
            responses_dir = mdfs_dir / "responses"
            contexts_dir.mkdir(exist_ok=True)
            responses_dir.mkdir(exist_ok=True)
            
            ctx = contexts_dir / "2025-01-15_120000__test.md"
            ctx.write_text("test context", encoding="utf-8")
            
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            result = log_cmd.execute()
            self.assertEqual(result, 0)

    def test_log_with_only_responses(self):
        """Test log command with only response files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            init_cmd = InitCommand(argparse.Namespace(dir=tmpdir))
            init_cmd.execute()
            
            # Create directories
            mdfs_dir = Path(tmpdir) / ".mdfs"
            mdfs_dir.mkdir(exist_ok=True)
            contexts_dir = mdfs_dir / "contexts"
            responses_dir = mdfs_dir / "responses"
            contexts_dir.mkdir(exist_ok=True)
            responses_dir.mkdir(exist_ok=True)
            
            resp = responses_dir / "2025-01-15_120000__test.md"
            resp.write_text("test response", encoding="utf-8")
            
            log_cmd = LogCommand(argparse.Namespace(dir=tmpdir))
            result = log_cmd.execute()
            self.assertEqual(result, 0)


if __name__ == "__main__":
    unittest.main()
