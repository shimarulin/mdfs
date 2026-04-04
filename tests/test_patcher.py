"""Tests for MDFS fuzzy patcher."""

import unittest
from mdfs.patcher import apply_patch, parse_hunks, PatchError


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


if __name__ == "__main__":
    unittest.main()
