"""Tests for MDFS fuzzy patcher."""

import unittest
from mdfs.core.patcher import apply_patch, parse_hunks, PatchError


class TestParseHunks(unittest.TestCase):

    def test_single_hunk(self):
        diff = (
            "--- a/file.py\n"
            "+++ b/file.py\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n"
            " line2\n"
            "+new_line\n"
            " line3"
        )
        hunks = parse_hunks(diff)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(hunks[0].old_start, 1)
        self.assertEqual(len(hunks[0].lines), 4)

    def test_multiple_hunks(self):
        diff = (
            "--- a/f.py\n"
            "+++ b/f.py\n"
            "@@ -1,2 +1,2 @@\n"
            "-old\n"
            "+new\n"
            " keep\n"
            "@@ -10,2 +10,3 @@\n"
            " ctx\n"
            "+added\n"
            " ctx2\n"
        )
        hunks = parse_hunks(diff)
        self.assertEqual(len(hunks), 2)


class TestApplyPatch(unittest.TestCase):

    def test_simple_addition(self):
        original = "line1\nline2\nline3"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n line2\n+inserted\n line3"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "line1\nline2\ninserted\nline3")

    def test_simple_removal(self):
        original = "line1\nline2\nline3"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,3 +1,2 @@\n"
            " line1\n-line2\n line3"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "line1\nline3")

    def test_replacement(self):
        original = "aaa\nbbb\nccc"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,3 +1,3 @@\n"
            " aaa\n-bbb\n+BBB\n ccc"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "aaa\nBBB\nccc")

    def test_fuzzy_wrong_line_number(self):
        original = "header\n\ndef foo():\n    pass\n\ndef bar():\n    pass"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -5,2 +5,3 @@\n"
            " def bar():\n     pass\n+    return True"
        )
        result = apply_patch(original, diff)
        self.assertIn("return True", result)
        self.assertIn("def foo():", result)

    def test_whitespace_tolerance(self):
        original = "line1  \nline2\nline3"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n line2\n+new\n line3"
        )
        result = apply_patch(original, diff)
        self.assertIn("new", result)

    def test_no_match_raises(self):
        original = "aaa\nbbb\nccc"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,3 +1,3 @@\n"
            " xxx\n-yyy\n+zzz\n www"
        )
        with self.assertRaises(PatchError):
            apply_patch(original, diff)

    def test_context_at_file_start(self):
        """Test fuzzy matching when context is at the beginning of file."""
        original = "first\nsecond\nthird\nfourth"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,2 +1,3 @@\n"
            " first\n second\n+inserted"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "first\nsecond\ninserted\nthird\nfourth")

    def test_context_at_file_end(self):
        """Test fuzzy matching when context is at the end of file."""
        original = "first\nsecond\nthird\nlast"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -3,2 +3,3 @@\n"
            " third\n last\n+appended"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "first\nsecond\nthird\nlast\nappended")

    def test_fuzzy_with_trailing_whitespace(self):
        """Test fuzzy matching tolerates trailing whitespace differences."""
        original = "line1  \nline2  \nline3"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n line2\n+new_line\n line3"
        )
        result = apply_patch(original, diff)
        self.assertIn("new_line", result)

    def test_empty_diff(self):
        """Test that empty diff returns original content."""
        original = "line1\nline2\nline3"
        diff = "--- a/f\n+++ b/f\n"
        result = apply_patch(original, diff)
        self.assertEqual(result, original)

    def test_multiple_similar_blocks(self):
        """Test fuzzy matching with multiple similar context blocks."""
        original = (
            "def foo():\n"
            "    pass\n"
            "\n"
            "def bar():\n"
            "    pass\n"
            "\n"
            "def baz():\n"
            "    pass"
        )
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -7,2 +7,3 @@\n"
            " def baz():\n     pass\n+    return 42"
        )
        result = apply_patch(original, diff)
        self.assertIn("return 42", result)
        self.assertIn("def foo():", result)
        self.assertIn("def bar():", result)

    def test_fuzzy_with_hint_offset(self):
        """Test fuzzy matching when actual line is far from hint."""
        original = (
            "line0\n"
            "line1\n"
            "line2\n"
            "target_line\n"
            "line4\n"
            "line5"
        )
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -2,3 +2,4 @@\n"
            " line1\n line2\n target_line\n+inserted"
        )
        result = apply_patch(original, diff)
        self.assertIn("inserted", result)
        self.assertIn("target_line", result)

    def test_single_line_file(self):
        """Test patching a single-line file."""
        original = "single_line"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,1 +1,2 @@\n"
            " single_line\n+new_line"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "single_line\nnew_line")

    def test_empty_line_in_context(self):
        """Test that empty lines in context are handled correctly."""
        original = "line1\n\nline3"
        diff = (
            "--- a/f\n+++ b/f\n"
            "@@ -1,3 +1,4 @@\n"
            " line1\n \n+inserted\n line3"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "line1\n\ninserted\nline3")


if __name__ == "__main__":
    unittest.main()
