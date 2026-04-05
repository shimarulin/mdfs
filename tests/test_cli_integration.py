"""Integration tests for MDFS CLI commands."""

import argparse
import shutil
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from mdfs.__main__ import (
    cmd_bundle,
    cmd_extract,
    cmd_init,
    cmd_paste,
    _make_filename,
)


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
        cmd_bundle(args)

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
        cmd_bundle(args)

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
        cmd_bundle(args)

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
        cmd_extract(args)

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
        cmd_extract(args)

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
        cmd_extract(args)

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

    @patch("mdfs.__main__._get_clipboard")
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
        cmd_paste(args)

        # Check response file was created
        responses = list((self.project_root / ".mdfs" / "responses").glob("*.md"))
        self.assertEqual(len(responses), 1)
        self.assertIn("response1", responses[0].name)

    @patch("mdfs.__main__._get_clipboard")
    def test_paste_and_extract(self, mock_clipboard):
        """Test paste with extract flag."""
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
        cmd_paste(args)

        # Check response was saved
        responses = list((self.project_root / ".mdfs" / "responses").glob("*.md"))
        self.assertEqual(len(responses), 1)

        # Check file was extracted
        new_file = self.project_root / "src" / "new.py"
        self.assertTrue(new_file.exists())

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
        cmd_init(argparse.Namespace(dir=str(self.project_root)))
        self.assertTrue((self.project_root / ".mdfs").is_dir())

        # Step 2: Create source file
        src = self.project_root / "src"
        src.mkdir()
        main_py = src / "main.py"
        main_py.write_text("def greet():\n    print('hello')\n", encoding="utf-8")

        # Step 3: Bundle
        cmd_bundle(
            argparse.Namespace(
                dir=str(self.project_root),
                files=["src/main.py"],
                label="initial",
                system_prompt=None,
                output=None,
            )
        )

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
        cmd_extract(
            argparse.Namespace(
                dir=str(self.project_root),
                input=str(response_file),
                dry_run=False,
            )
        )

        # Step 7: Verify patches applied
        modified_content = main_py.read_text(encoding="utf-8")
        self.assertIn("print('world')", modified_content)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
