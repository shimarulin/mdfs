"""Tests for MDFS extractor."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mdfs.extractor import extract


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

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
