"""Tests for MDFS parser."""

import unittest
from mdfs.parser import parse, BlockType


class TestParse(unittest.TestCase):

    def test_single_file_block(self):
        md = (
            "### `src/main.py`\n"
            "\n"
            "<!-- file: src/main.py -->\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
        )
        blocks = parse(md)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].type, BlockType.FILE)
        self.assertEqual(blocks[0].path, "src/main.py")
        self.assertEqual(blocks[0].content, "print('hello')")
        self.assertEqual(blocks[0].lang, "python")

    def test_patch_block(self):
        md = (
            "### `src/main.py`\n"
            "\n"
            "<!-- patch: src/main.py -->\n"
            "```diff\n"
            "--- a/src/main.py\n"
            "+++ b/src/main.py\n"
            "@@ -1 +1,2 @@\n"
            " print('hello')\n"
            "+print('world')\n"
            "```\n"
        )
        blocks = parse(md)
        self.assertEqual(len(blocks), 1)
        self.assertEqual(blocks[0].type, BlockType.PATCH)

    def test_nested_fences(self):
        md = (
            "### `docs/README.md`\n"
            "\n"
            "<!-- file: docs/README.md -->\n"
            "````markdown\n"
            "# README\n"
            "\n"
            "```bash\n"
            "echo hello\n"
            "```\n"
            "````\n"
        )
        blocks = parse(md)
        self.assertEqual(len(blocks), 1)
        self.assertIn("```bash", blocks[0].content)

    def test_multiple_blocks(self):
        md = (
            "<!-- file: a.py -->\n"
            "```python\n"
            "a = 1\n"
            "```\n"
            "\n"
            "<!-- file: b.py -->\n"
            "```python\n"
            "b = 2\n"
            "```\n"
        )
        blocks = parse(md)
        self.assertEqual(len(blocks), 2)


if __name__ == "__main__":
    unittest.main()
