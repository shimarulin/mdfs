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
            "<!-- file: src/main.py -->\n"
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
            "<!-- patch: src/main.py -->\n"
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
            "<!-- patch: nope.py -->\n"
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
        md = "<!-- file: new.py -->\n```python\npass\n```\n"
        actions = extract(md, self.tmpdir, dry_run=True)
        self.assertEqual(actions[0].action, "write")
        self.assertFalse((Path(self.tmpdir) / "new.py").exists())

    def test_apply_patch_error(self):
        """Test that PatchError is caught and reported as action error."""
        src = Path(self.tmpdir) / "src"
        src.mkdir(parents=True)
        (src / "main.py").write_text("aaa\nbbb\nccc\n", encoding="utf-8")

        md = (
            "<!-- patch: src/main.py -->\n"
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
            "<!-- patch: src/main.py -->\n"
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

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
