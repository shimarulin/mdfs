"""Tests for MDFS parser."""

import unittest
from mdfs.core.parser import parse, BlockType


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

    def test_fence_depth_validation_correct(self):
        """Test that correct fence nesting passes validation."""
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
        self.assertFalse(blocks[0].fence_depth_error)
        self.assertIsNone(blocks[0].normalized_content)

    def test_fence_depth_validation_incorrect(self):
        """Test that incorrect fence nesting is detected."""
        md = (
            "### `docs/README.md`\n"
            "\n"
            "<!-- file: docs/README.md -->\n"
            "```markdown\n"
            "# README\n"
            "\n"
            "```bash\n"
            "echo hello\n"
            "```\n"
            "```\n"
        )
        blocks = parse(md)
        self.assertEqual(len(blocks), 1)
        self.assertTrue(blocks[0].fence_depth_error)
        self.assertIsNotNone(blocks[0].normalized_content)

    def test_fence_depth_normalization(self):
        """Test that fence depths are normalized correctly."""
        md = (
            "<!-- file: test.md -->\n"
            "```markdown\n"
            "# Test\n"
            "\n"
            "```bash\n"
            "echo hello\n"
            "```\n"
            "```\n"
        )
        blocks = parse(md)
        self.assertTrue(blocks[0].fence_depth_error)
        normalized = blocks[0].normalized_content
        # Content should contain bash fence
        self.assertIn("```bash", normalized)
        self.assertIn("echo hello", normalized)
        # Should not contain markdown fence (that's the outer fence, not content)
        self.assertNotIn("````markdown", normalized)

    def test_no_fence_depth_error_for_simple_code(self):
        """Test that simple code blocks without nesting don't have errors."""
        md = (
            "<!-- file: simple.py -->\n"
            "```python\n"
            "print('hello')\n"
            "```\n"
        )
        blocks = parse(md)
        self.assertFalse(blocks[0].fence_depth_error)


if __name__ == "__main__":
    unittest.main()
