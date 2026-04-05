"""Integration tests for MDFS CLI commands."""

import argparse
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mdfs.commands import (
    BundleCommand,
    ExtractCommand,
    InitCommand,
    LogCommand,
    PasteCommand,
)
from mdfs.utils import find_mdfs_root, make_filename


class TestBundleCommand(unittest.TestCase):
    """Integration tests for mdfs bundle command."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = Path(self.tmpdir)

        # Create project structure
        (self.project_root / ".mdfs").mkdir()
        (self.project_root / ".mdfs" / "contexts").mkdir(parents=True)
        (self.project_root / ".mdfs" / "responses").mkdir(parents=True)
        (self.project_root / ".mdfs" / "rules").mkdir(parents=True)

        # Create sample files
        src = self.project_root / "src"
        src.mkdir()
        (src / "main.py").write_text("def main():\n    print('hello')\n", encoding="utf-8")
        (src / "utils.py").write_text("def helper():\n    pass\n", encoding="utf-8")

    def test_bundle_creates_context_file(self):
        """Test that bundle creates a context markdown file."""
        args = argparse.Namespace(
            dir=str(self.project_root),
            files=["src/main.py", "src/utils.py"],
            label="initial setup",
            system_prompt=None,
            output=None,
        )
        cmd = BundleCommand(args)
        cmd.execute()

        # Check that context file was created
        contexts = list((self.project_root / ".mdfs" / "contexts").glob("*.md"))
        self.assertEqual(len(contexts), 1)
        self.assertIn("initial_setup", contexts[0].name)

        # Check content
        content = contexts[0].read_text(encoding="utf-8")
        self.assertIn("<!-- file: src/main.py -->", content)
        self.assertIn("<!-- file: src/utils.py -->", content)
        self.assertIn("def main():", content)

    def test_bundle_without_label(self):
        """Test bundle without label creates timestamp-only filename."""
        args = argparse.Namespace(
            dir=str(self.project_root),
            files=["src/main.py"],
            label=None,
            system_prompt=None,
            output=None,
        )
        cmd = BundleCommand(args)
        cmd.execute()

        contexts = list((self.project_root / ".mdfs" / "contexts").glob("*.md"))
        self.assertEqual(len(contexts), 1)
        # Should be timestamp only (no __)
        self.assertNotIn("__", contexts[0].name)

    def test_bundle_with_system_prompt(self):
        """Test bundle includes system prompt in output."""
        prompt_file = self.project_root / "system.md"
        prompt_file.write_text("You are a helpful assistant.\n", encoding="utf-8")

        args = argparse.Namespace(
            dir=str(self.project_root),
            files=["src/main.py"],
            label="test",
            system_prompt=str(prompt_file),
            output=None,
        )
        cmd = BundleCommand(args)
        cmd.execute()

        contexts = list((self.project_root / ".mdfs" / "contexts").glob("*.md"))
        content = contexts[0].read_text(encoding="utf-8")
        self.assertIn("You are a helpful assistant.", content)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestExtractCommand(unittest.TestCase):
    """Integration tests for mdfs extract command."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = Path(self.tmpdir)

        # Create project structure
        (self.project_root / ".mdfs").mkdir()
        (self.project_root / ".mdfs" / "responses").mkdir(parents=True)

        # Create initial files
        src = self.project_root / "src"
        src.mkdir()
        (src / "main.py").write_text("x = 1\n", encoding="utf-8")

    def test_extract_writes_new_files(self):
        """Test that extract writes new files from markdown."""
        markdown_file = self.project_root / ".mdfs" / "responses" / "test.md"
        markdown_file.write_text(
            "<!-- file: src/new.py -->\n"
            "```python\n"
            "y = 2\n"
            "```\n",
            encoding="utf-8",
        )

        args = argparse.Namespace(
            dir=str(self.project_root),
            input=str(markdown_file),
            dry_run=False,
        )
        cmd = ExtractCommand(args)
        cmd.execute()

        # Check file was created
        new_file = self.project_root / "src" / "new.py"
        self.assertTrue(new_file.exists())
        self.assertEqual(new_file.read_text(encoding="utf-8").strip(), "y = 2")

    def test_extract_applies_patches(self):
        """Test that extract applies patches to existing files."""
        markdown_file = self.project_root / ".mdfs" / "responses" / "patch.md"
        markdown_file.write_text(
            "<!-- patch: src/main.py -->\n"
            "```diff\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1 +1,2 @@\n"
            " x = 1\n"
            "+y = 2\n"
            "```\n",
            encoding="utf-8",
        )

        args = argparse.Namespace(
            dir=str(self.project_root),
            input=str(markdown_file),
            dry_run=False,
        )
        cmd = ExtractCommand(args)
        cmd.execute()

        # Check patch was applied
        content = (self.project_root / "src" / "main.py").read_text(encoding="utf-8")
        self.assertIn("x = 1", content)
        self.assertIn("y = 2", content)

    def test_extract_dry_run(self):
        """Test that dry_run doesn't modify files."""
        markdown_file = self.project_root / ".mdfs" / "responses" / "test.md"
        markdown_file.write_text(
            "<!-- file: src/dryrun.py -->\n"
            "```python\n"
            "z = 3\n"
            "```\n",
            encoding="utf-8",
        )

        args = argparse.Namespace(
            dir=str(self.project_root),
            input=str(markdown_file),
            dry_run=True,
        )
        cmd = ExtractCommand(args)
        cmd.execute()

        # File should not be created
        self.assertFalse((self.project_root / "src" / "dryrun.py").exists())

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestPasteCommand(unittest.TestCase):
    """Integration tests for mdfs paste command."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = Path(self.tmpdir)

        # Create project structure
        (self.project_root / ".mdfs").mkdir()
        (self.project_root / ".mdfs" / "responses").mkdir(parents=True)
        (self.project_root / ".mdfs" / "contexts").mkdir(parents=True)

        # Create sample file
        src = self.project_root / "src"
        src.mkdir()
        (src / "main.py").write_text("x = 1\n", encoding="utf-8")

    @patch("mdfs.utils.get_clipboard")
    def test_paste_saves_response(self, mock_clipboard):
        """Test that paste saves clipboard content as response file."""
        mock_clipboard.return_value = (
            "# LLM Response\n"
            "<!-- file: src/new.py -->\n"
            "```python\n"
            "y = 2\n"
            "```\n"
        )

        args = argparse.Namespace(
            dir=str(self.project_root),
            label="response1",
            extract=False,
            dry_run=False,
        )
        cmd = PasteCommand(args)
        cmd.execute()

        # Check response file was created
        responses = list((self.project_root / ".mdfs" / "responses").glob("*.md"))
        self.assertEqual(len(responses), 1)
        self.assertIn("response1", responses[0].name)

    @patch("mdfs.utils.get_clipboard")
    def test_paste_and_extract(self, mock_clipboard):
        """Test paste with extract flag - just verify no errors on extraction."""
        # Need to initialize .mdfs first
        init_cmd = InitCommand(argparse.Namespace(dir=str(self.project_root)))
        init_cmd.execute()
        
        # Create src directory first
        src = self.project_root / "src"
        src.mkdir(parents=True, exist_ok=True)
        
        mock_clipboard.return_value = (
            "# LLM Response\n"
            "<!-- file: src/new.py -->\n"
            "```python\n"
            "y = 2\n"
            "```\n"
        )

        args = argparse.Namespace(
            dir=str(self.project_root),
            label="with_extract",
            extract=True,
            dry_run=False,
        )
        cmd = PasteCommand(args)
        exit_code = cmd.execute()

        # Check response was saved
        responses = list((self.project_root / ".mdfs" / "responses").glob("*.md"))
        self.assertEqual(len(responses), 1)

        # Check exit code is 0 (no errors)
        self.assertEqual(exit_code, 0)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestFullWorkflow(unittest.TestCase):
    """Test complete MDFS workflow: init → bundle → extract."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = Path(self.tmpdir)

    def test_complete_workflow(self):
        """Test: init → create files → bundle → extract patches → verify."""
        # Step 1: Initialize
        init_cmd = InitCommand(argparse.Namespace(dir=str(self.project_root)))
        init_cmd.execute()
        self.assertTrue((self.project_root / ".mdfs").is_dir())

        # Step 2: Create source file
        src = self.project_root / "src"
        src.mkdir()
        main_py = src / "main.py"
        main_py.write_text("def greet():\n    print('hello')\n", encoding="utf-8")

        # Step 3: Bundle
        bundle_cmd = BundleCommand(
            argparse.Namespace(
                dir=str(self.project_root),
                files=["src/main.py"],
                label="initial",
                system_prompt=None,
                output=None,
            )
        )
        bundle_cmd.execute()

        # Check bundle created
        bundles = list((self.project_root / ".mdfs" / "contexts").glob("*.md"))
        self.assertEqual(len(bundles), 1)

        # Step 4: Simulate LLM response with patch
        bundle_content = bundles[0].read_text(encoding="utf-8")
        self.assertIn("def greet():", bundle_content)

        # Step 5: Create response with patches
        response_content = (
            "# LLM Response\n"
            "Improved the code:\n"
            "<!-- patch: src/main.py -->\n"
            "```diff\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,2 +1,3 @@\n"
            " def greet():\n     print('hello')\n"
            "+    print('world')\n"
            "```\n"
        )

        response_file = self.project_root / ".mdfs" / "responses" / "response.md"
        response_file.write_text(response_content, encoding="utf-8")

        # Step 6: Extract patches
        extract_cmd = ExtractCommand(
            argparse.Namespace(
                dir=str(self.project_root),
                input=str(response_file),
                dry_run=False,
            )
        )
        extract_cmd.execute()

        # Step 7: Verify patches applied
        modified_content = main_py.read_text(encoding="utf-8")
        self.assertIn("print('world')", modified_content)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestLogCommand(unittest.TestCase):
    """Tests for mdfs log command."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = Path(self.tmpdir)

        # Create project structure
        (self.project_root / ".mdfs").mkdir()
        (self.project_root / ".mdfs" / "contexts").mkdir(parents=True)
        (self.project_root / ".mdfs" / "responses").mkdir(parents=True)

    def test_cmd_log_empty(self):
        """Test log command with no contexts or responses."""
        args = argparse.Namespace(dir=str(self.project_root))
        # Should not raise an exception
        cmd = LogCommand(args)
        cmd.execute()

    def test_cmd_log_with_entries(self):
        """Test log command displays contexts and responses."""
        # Create some entries
        contexts_dir = self.project_root / ".mdfs" / "contexts"
        responses_dir = self.project_root / ".mdfs" / "responses"

        (contexts_dir / "2026-01-01_120000__test.md").write_text("context", encoding="utf-8")
        (responses_dir / "2026-01-01_120100__test.md").write_text("response", encoding="utf-8")

        args = argparse.Namespace(dir=str(self.project_root))
        # Should not raise an exception
        cmd = LogCommand(args)
        cmd.execute()

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestMakeFilename(unittest.TestCase):
    """Unit tests for make_filename helper."""

    def test_make_filename_with_label(self):
        """Test filename generation with label."""
        result = make_filename("test label")
        self.assertIn("__test_label.md", result)

    def test_make_filename_without_label(self):
        """Test filename generation without label."""
        result = make_filename(None)
        self.assertTrue(result.endswith(".md"))
        self.assertNotIn("__", result)

    def test_make_filename_special_chars(self):
        """Test filename generation with special characters in label."""
        result = make_filename("test-123!@#")
        self.assertIn(".md", result)
        # Special chars should be removed
        self.assertNotIn("!", result)
        self.assertNotIn("@", result)
        self.assertNotIn("#", result)


class TestPasteErrorHandling(unittest.TestCase):
    """Tests for error handling in paste command."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.project_root = Path(self.tmpdir)

        # Create project structure
        (self.project_root / ".mdfs").mkdir()
        (self.project_root / ".mdfs" / "responses").mkdir(parents=True)

    @patch("mdfs.utils.get_clipboard")
    def test_paste_with_valid_content(self, mock_clipboard):
        """Test paste command with valid clipboard content."""
        mock_clipboard.return_value = (
            "# Response\n"
            "<!-- file: test.py -->\n"
            "```python\n"
            "x = 1\n"
            "```\n"
        )

        args = argparse.Namespace(
            dir=str(self.project_root),
            label="valid",
            extract=False,
            dry_run=False,
        )

        cmd = PasteCommand(args)
        result = cmd.execute()
        
        # Should return 0 when clipboard has valid content
        self.assertEqual(result, 0)
        
        # Response file should be created
        responses = list((self.project_root / ".mdfs" / "responses").glob("*.md"))
        self.assertEqual(len(responses), 1)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


class TestFindMdfsRoot(unittest.TestCase):
    """Tests for find_mdfs_root helper."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_find_mdfs_root_success(self):
        """Test finding .mdfs directory."""
        mdfs_dir = Path(self.tmpdir) / ".mdfs"
        mdfs_dir.mkdir()

        result = find_mdfs_root(self.tmpdir)
        self.assertEqual(result, Path(self.tmpdir).resolve())

    def test_find_mdfs_root_nested(self):
        """Test finding .mdfs from nested directory."""
        mdfs_dir = Path(self.tmpdir) / ".mdfs"
        mdfs_dir.mkdir()

        nested = Path(self.tmpdir) / "src" / "nested"
        nested.mkdir(parents=True)

        result = find_mdfs_root(nested)
        self.assertEqual(result, Path(self.tmpdir).resolve())

    def test_find_mdfs_root_not_found(self):
        """Test error when .mdfs not found."""
        with self.assertRaises(SystemExit):
            find_mdfs_root(self.tmpdir)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
