"""Tests for MDFS extractor."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mdfs.core.extractor import extract


class TestExtract(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()

    def test_write_new_file(self):
        md = (
            "<!-- file: \"src/main.py\" -->\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
        )
        actions = extract(md, self.tmpdir)
        self.assertEqual(actions[0].action, "write")
        written = (Path(self.tmpdir) / "src" / "main.py").read_text(encoding="utf-8")
        self.assertEqual(written.strip(), "print('hello')")

    def test_apply_patch(self):
        src = Path(self.tmpdir) / "src"
        src.mkdir(parents=True)
        (src / "main.py").write_text("line1\nline2\nline3\n", encoding="utf-8")

        md = (
            "<!-- patch: \"src/main.py\" -->\n"
            "```diff\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n"
            " line2\n"
            "+inserted\n"
            " line3\n"
            "```\n"
        )
        actions = extract(md, self.tmpdir)
        self.assertEqual(actions[0].action, "patch")
        result = (src / "main.py").read_text(encoding="utf-8")
        self.assertIn("inserted", result)

    def test_patch_missing_file(self):
        md = (
            "<!-- patch: \"nope.py\" -->\n"
            "```diff\n"
            "--- a/nope.py\n"
            "+++ b/nope.py\n"
            "@@ -1 +1,2 @@\n"
            " x\n"
            "+y\n"
            "```\n"
        )
        actions = extract(md, self.tmpdir)
        self.assertEqual(actions[0].action, "error")

    def test_dry_run(self):
        md = "<!-- file: \"new.py\" -->\n```python\npass\n```\n"
        actions = extract(md, self.tmpdir, dry_run=True)
        self.assertEqual(actions[0].action, "write")
        self.assertFalse((Path(self.tmpdir) / "new.py").exists())

    def test_apply_patch_error(self):
        """Test that PatchError is caught and reported as action error."""
        src = Path(self.tmpdir) / "src"
        src.mkdir(parents=True)
        (src / "main.py").write_text("aaa\nbbb\nccc\n", encoding="utf-8")

        md = (
            "<!-- patch: \"src/main.py\" -->\n"
            "```diff\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,3 @@\n"
            " xxx\n-yyy\n+zzz\n www\n"
            "```\n"
        )
        actions = extract(md, self.tmpdir)
        self.assertEqual(actions[0].action, "error")
        self.assertIn("cannot find context", actions[0].detail.lower())

    def test_patch_dry_run(self):
        """Test that dry-run mode works for patches."""
        src = Path(self.tmpdir) / "src"
        src.mkdir(parents=True)
        original_content = "line1\nline2\nline3\n"
        (src / "main.py").write_text(original_content, encoding="utf-8")

        md = (
            "<!-- patch: \"src/main.py\" -->\n"
            "```diff\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n"
            " line2\n"
            "+inserted\n"
            " line3\n"
            "```\n"
        )
        actions = extract(md, self.tmpdir, dry_run=True)
        self.assertEqual(actions[0].action, "patch")
        self.assertIn("dry-run", actions[0].detail)
        # File should not be modified
        result = (src / "main.py").read_text(encoding="utf-8")
        self.assertEqual(result, original_content)

    def test_extract_with_fence_depth_normalization(self):
        """Test that files with incorrect fence depth are normalized when extracted."""
        md = (
            "<!-- file: \"test.md\" -->\n"
            "```markdown\n"
            "# Test\n"
            "\n"
            "```bash\n"
            "echo hello\n"
            "```\n"
            "```\n"
        )
        actions = extract(md, self.tmpdir)
        self.assertEqual(actions[0].action, "write")
        self.assertIn("normalized", actions[0].detail.lower())
        
        # Check that file was written with normalized content
        written = (Path(self.tmpdir) / "test.md").read_text(encoding="utf-8")
        # File contains the normalized markdown
        self.assertIn("# Test", written)
        self.assertIn("```bash", written)
        self.assertIn("echo hello", written)

    def test_extract_without_fence_depth_error(self):
        """Test that files with correct fence depth are written as-is."""
        md = (
            "<!-- file: \"test.md\" -->\n"
            "````markdown\n"
            "# Test\n"
            "\n"
            "```bash\n"
            "echo hello\n"
            "```\n"
            "````\n"
        )
        actions = extract(md, self.tmpdir)
        self.assertEqual(actions[0].action, "write")
        # Should not have normalization detail
        self.assertNotIn("normalized", actions[0].detail.lower())
        
        # Check that file was written with original content (no outer fence)
        written = (Path(self.tmpdir) / "test.md").read_text(encoding="utf-8")
        self.assertIn("# Test", written)
        self.assertIn("```bash", written)

    def test_no_markers_found(self):
        """Test that info action is returned when no markers are found."""
        md = (
            "# This is just a Markdown document\n"
            "\n"
            "No file or patch markers here.\n"
        )
        actions = extract(md, self.tmpdir)
        self.assertEqual(len(actions), 1)
        self.assertEqual(actions[0].action, "info")
        self.assertIn("No markers found", actions[0].detail)

    def test_force_overwrite(self):
        """Test that force flag overwrites existing files without prompting."""
        src = Path(self.tmpdir) / "src"
        src.mkdir(parents=True)
        (src / "main.py").write_text("old content\n", encoding="utf-8")

        md = (
            "<!-- file: \"src/main.py\" -->\n"
            "```python\n"
            "new content\n"
            "```\n"
        )
        actions = extract(md, self.tmpdir, force=True)
        self.assertEqual(actions[0].action, "write")
        written = (src / "main.py").read_text(encoding="utf-8")
        self.assertIn("new content", written)

    def test_skip_action(self):
        """Test that skip action is returned for skipped files."""
        src = Path(self.tmpdir) / "src"
        src.mkdir(parents=True)
        original_content = "original\n"
        (src / "main.py").write_text(original_content, encoding="utf-8")

        md = (
            "<!-- file: \"src/main.py\" -->\n"
            "```python\n"
            "new content\n"
            "```\n"
        )
        # Simulate user choosing 'n' (skip)
        import io
        import sys
        old_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("n\n")
            actions = extract(md, self.tmpdir, force=False)
            self.assertEqual(actions[0].action, "skip")
            # File should not be modified
            written = (src / "main.py").read_text(encoding="utf-8")
            self.assertEqual(written, original_content)
        finally:
            sys.stdin = old_stdin

    def test_yes_to_all(self):
        """Test that Y (yes to all) works for multiple files."""
        src = Path(self.tmpdir) / "src"
        src.mkdir(parents=True)
        (src / "file1.py").write_text("old1\n", encoding="utf-8")
        (src / "file2.py").write_text("old2\n", encoding="utf-8")

        md = (
            "<!-- file: \"src/file1.py\" -->\n"
            "```python\n"
            "new1\n"
            "```\n"
            "<!-- file: \"src/file2.py\" -->\n"
            "```python\n"
            "new2\n"
            "```\n"
        )
        # Simulate user choosing 'Y' (yes to all) on first file
        import io
        import sys
        old_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("Y\n")
            actions = extract(md, self.tmpdir, force=False)
            # Both files should be written
            self.assertEqual(len([a for a in actions if a.action == "write"]), 2)
            file1 = (src / "file1.py").read_text(encoding="utf-8")
            file2 = (src / "file2.py").read_text(encoding="utf-8")
            self.assertIn("new1", file1)
            self.assertIn("new2", file2)
        finally:
            sys.stdin = old_stdin

    def test_no_to_all(self):
        """Test that N (no to all) works for multiple files."""
        src = Path(self.tmpdir) / "src"
        src.mkdir(parents=True)
        original1 = "old1\n"
        original2 = "old2\n"
        (src / "file1.py").write_text(original1, encoding="utf-8")
        (src / "file2.py").write_text(original2, encoding="utf-8")

        md = (
            "<!-- file: \"src/file1.py\" -->\n"
            "```python\n"
            "new1\n"
            "```\n"
            "<!-- file: \"src/file2.py\" -->\n"
            "```python\n"
            "new2\n"
            "```\n"
        )
        # Simulate user choosing 'N' (no to all) on first file
        import io
        import sys
        old_stdin = sys.stdin
        try:
            sys.stdin = io.StringIO("N\n")
            actions = extract(md, self.tmpdir, force=False)
            # Both files should be skipped
            self.assertEqual(len([a for a in actions if a.action == "skip"]), 2)
            file1 = (src / "file1.py").read_text(encoding="utf-8")
            file2 = (src / "file2.py").read_text(encoding="utf-8")
            self.assertEqual(file1, original1)
            self.assertEqual(file2, original2)
        finally:
            sys.stdin = old_stdin

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
