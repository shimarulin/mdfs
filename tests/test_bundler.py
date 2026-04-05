"""Tests for MDFS bundler."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mdfs.core.bundler import bundle


class TestBundle(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        src = Path(self.tmpdir) / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (src / "utils.py").write_text("def helper():\n    pass\n", encoding="utf-8")

    def test_basic_bundle(self):
        result = bundle(self.tmpdir, ["src/main.py", "src/utils.py"])
        self.assertIn("<!-- file: src/main.py -->", result)
        self.assertIn("<!-- file: src/utils.py -->", result)
        self.assertIn("print('hello')", result)

    def test_missing_file(self):
        result = bundle(self.tmpdir, ["nonexistent.py"])
        self.assertIn("File not found", result)

    def test_with_system_prompt(self):
        result = bundle(self.tmpdir, ["src/main.py"], system_prompt="You are helpful.")
        self.assertIn("You are helpful.", result)
        self.assertIn("<!-- file: src/main.py -->", result)

    def test_nested_fences_get_longer_fence(self):
        md_file = Path(self.tmpdir) / "doc.md"
        md_file.write_text("# Doc\n\n```python\nprint(1)\n```\n", encoding="utf-8")
        result = bundle(self.tmpdir, ["doc.md"])
        self.assertIn("````", result)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
