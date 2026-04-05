"""Tests for MDFS fuzzy patcher."""

import unittest
from mdfs.core.patcher import (
    apply_patch,
    parse_hunks,
    PatchError,
    _context_and_removals,
    _find_match,
    DiffLine,
    Hunk,
)


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


class TestContextAndRemovals(unittest.TestCase):
    """Tests for _context_and_removals helper function."""

    def test_only_context(self):
        """Test hunk with only context lines."""
        hunk = Hunk(1, 3, 1, 3, [
            DiffLine(" ", "line1"),
            DiffLine(" ", "line2"),
            DiffLine(" ", "line3"),
        ])
        result = _context_and_removals(hunk)
        self.assertEqual(result, ["line1", "line2", "line3"])

    def test_only_removals(self):
        """Test hunk with only removal lines."""
        hunk = Hunk(1, 3, 1, 0, [
            DiffLine("-", "old1"),
            DiffLine("-", "old2"),
            DiffLine("-", "old3"),
        ])
        result = _context_and_removals(hunk)
        self.assertEqual(result, ["old1", "old2", "old3"])

    def test_mixed_context_and_removals(self):
        """Test hunk with both context and removal lines."""
        hunk = Hunk(1, 3, 1, 2, [
            DiffLine(" ", "keep1"),
            DiffLine("-", "remove"),
            DiffLine(" ", "keep2"),
        ])
        result = _context_and_removals(hunk)
        self.assertEqual(result, ["keep1", "remove", "keep2"])

    def test_with_additions(self):
        """Test that addition lines are not included."""
        hunk = Hunk(1, 2, 1, 3, [
            DiffLine(" ", "keep"),
            DiffLine("+", "added"),
            DiffLine("-", "removed"),
        ])
        result = _context_and_removals(hunk)
        self.assertEqual(result, ["keep", "removed"])

    def test_empty_hunk(self):
        """Test empty hunk."""
        hunk = Hunk(1, 0, 1, 0, [])
        result = _context_and_removals(hunk)
        self.assertEqual(result, [])

    def test_empty_lines_in_hunk(self):
        """Test that empty lines are preserved."""
        hunk = Hunk(1, 3, 1, 3, [
            DiffLine(" ", "line1"),
            DiffLine(" ", ""),
            DiffLine(" ", "line3"),
        ])
        result = _context_and_removals(hunk)
        self.assertEqual(result, ["line1", "", "line3"])


class TestFindMatch(unittest.TestCase):
    """Tests for _find_match helper function."""

    def test_empty_pattern(self):
        """Test with empty pattern returns hint-1."""
        file_lines = ["line1", "line2", "line3"]
        result = _find_match(file_lines, [], 3)
        self.assertEqual(result, 2)

    def test_exact_match_at_hint(self):
        """Test exact match at hint position."""
        file_lines = ["line1", "line2", "line3"]
        pattern = ["line2"]
        result = _find_match(file_lines, pattern, 2)
        self.assertEqual(result, 1)

    def test_exact_match_offset_from_hint(self):
        """Test exact match away from hint position."""
        file_lines = ["line1", "line2", "line3", "line4", "line5"]
        pattern = ["line4"]
        result = _find_match(file_lines, pattern, 2)
        self.assertEqual(result, 3)

    def test_multiline_pattern_exact(self):
        """Test exact match with multiple lines."""
        file_lines = ["a", "b", "c", "d"]
        pattern = ["b", "c"]
        result = _find_match(file_lines, pattern, 2)
        self.assertEqual(result, 1)

    def test_stripped_match(self):
        """Test fuzzy match with trailing whitespace."""
        file_lines = ["line1  ", "line2  ", "line3"]
        pattern = ["line1", "line2"]
        result = _find_match(file_lines, pattern, 1)
        self.assertEqual(result, 0)

    def test_pattern_larger_than_file(self):
        """Test pattern longer than file."""
        file_lines = ["line1", "line2"]
        pattern = ["line1", "line2", "line3"]
        result = _find_match(file_lines, pattern, 1)
        self.assertIsNone(result)

    def test_no_match_found(self):
        """Test when pattern doesn't exist."""
        file_lines = ["aaa", "bbb", "ccc"]
        pattern = ["xxx", "yyy"]
        result = _find_match(file_lines, pattern, 2)
        self.assertIsNone(result)

    def test_match_at_file_start(self):
        """Test match at beginning of file."""
        file_lines = ["first", "second", "third"]
        pattern = ["first", "second"]
        result = _find_match(file_lines, pattern, 1)
        self.assertEqual(result, 0)

    def test_match_at_file_end(self):
        """Test match at end of file."""
        file_lines = ["first", "second", "last"]
        pattern = ["second", "last"]
        result = _find_match(file_lines, pattern, 2)
        self.assertEqual(result, 1)

    def test_single_line_file(self):
        """Test matching in single-line file."""
        file_lines = ["only_line"]
        pattern = ["only_line"]
        result = _find_match(file_lines, pattern, 1)
        self.assertEqual(result, 0)

    def test_multiple_similar_blocks(self):
        """Test fuzzy match finds correct block despite similarities."""
        file_lines = [
            "def foo():",
            "    pass",
            "",
            "def bar():",
            "    pass",
            "",
            "def baz():",
            "    pass",
        ]
        pattern = ["def baz():", "    pass"]
        result = _find_match(file_lines, pattern, 7)
        self.assertEqual(result, 6)


class TestParseHunksExtended(unittest.TestCase):
    """Extended tests for parse_hunks function."""

    def test_hunk_without_old_count(self):
        """Test hunk without old_count defaults to 1."""
        diff = (
            "@@ -1 +1,2 @@\n"
            " context\n"
            "+added"
        )
        hunks = parse_hunks(diff)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(hunks[0].old_count, 1)

    def test_hunk_without_new_count(self):
        """Test hunk without new_count defaults to 1."""
        diff = (
            "@@ -1,2 +1 @@\n"
            " context\n"
            "-removed"
        )
        hunks = parse_hunks(diff)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(hunks[0].new_count, 1)

    def test_consecutive_hunks(self):
        """Test multiple hunks in sequence."""
        diff = (
            "@@ -1,1 +1,2 @@\n"
            " first\n"
            "+added1\n"
            "@@ -5,1 +6,2 @@\n"
            " fifth\n"
            "+added2"
        )
        hunks = parse_hunks(diff)
        self.assertEqual(len(hunks), 2)
        self.assertEqual(hunks[0].old_start, 1)
        self.assertEqual(hunks[1].old_start, 5)

    def test_hunk_with_only_additions(self):
        """Test hunk that only adds lines."""
        diff = (
            "@@ -1,0 +1,2 @@\n"
            "+new1\n"
            "+new2"
        )
        hunks = parse_hunks(diff)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(len([l for l in hunks[0].lines if l.type == "+"]), 2)

    def test_hunk_with_only_removals(self):
        """Test hunk that only removes lines."""
        diff = (
            "@@ -1,2 +1,0 @@\n"
            "-old1\n"
            "-old2"
        )
        hunks = parse_hunks(diff)
        self.assertEqual(len(hunks), 1)
        self.assertEqual(len([l for l in hunks[0].lines if l.type == "-"]), 2)

    def test_empty_diff(self):
        """Test empty diff returns empty list."""
        hunks = parse_hunks("")
        self.assertEqual(hunks, [])

    def test_diff_with_headers_only(self):
        """Test diff with only headers, no hunks."""
        diff = "--- a/file\n+++ b/file"
        hunks = parse_hunks(diff)
        self.assertEqual(hunks, [])

    def test_empty_lines_in_hunk(self):
        """Test that empty lines are preserved in hunks."""
        diff = (
            "@@ -1,3 +1,3 @@\n"
            " line1\n"
            " \n"
            " line3"
        )
        hunks = parse_hunks(diff)
        self.assertEqual(len(hunks[0].lines), 3)
        self.assertEqual(hunks[0].lines[1].text, "")


class TestApplyPatchExtended(unittest.TestCase):
    """Extended tests for apply_patch function."""

    def test_multiple_hunks_sequential(self):
        """Test applying multiple sequential hunks."""
        original = "a\nb\nc\nd\ne\nf"
        diff = (
            "@@ -1,2 +1,3 @@\n"
            " a\n b\n+inserted1\n"
            "@@ -5,1 +6,2 @@\n"
            " e\n f\n+inserted2"
        )
        result = apply_patch(original, diff)
        self.assertIn("inserted1", result)
        self.assertIn("inserted2", result)

    def test_patch_with_offset_accumulation(self):
        """Test that offset is properly accumulated across hunks."""
        original = "line1\nline2\nline3\nline4\nline5"
        diff = (
            "@@ -1,1 +1,2 @@\n"
            " line1\n+new1\n"
            "@@ -3,1 +4,2 @@\n"
            " line3\n+new3"
        )
        result = apply_patch(original, diff)
        lines = result.split("\n")
        self.assertEqual(lines[0], "line1")
        self.assertEqual(lines[1], "new1")
        self.assertIn("new3", result)

    def test_empty_file_patch(self):
        """Test patching empty file."""
        original = ""
        diff = (
            "@@ -0,0 +1,1 @@\n"
            "+content"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "content\n")

    def test_add_at_file_start(self):
        """Test adding lines at start of file."""
        original = "existing"
        diff = (
            "@@ -1,0 +1,1 @@\n"
            "+new"
        )
        result = apply_patch(original, diff)
        self.assertTrue(result.startswith("new"))

    def test_add_at_file_end(self):
        """Test adding lines at end of file."""
        original = "line1\nline2"
        diff = (
            "@@ -2,1 +2,2 @@\n"
            " line2\n+appended"
        )
        result = apply_patch(original, diff)
        self.assertTrue(result.endswith("appended"))

    def test_replace_entire_line(self):
        """Test replacing entire line."""
        original = "old_content"
        diff = (
            "@@ -1,1 +1,1 @@\n"
            "-old_content\n+new_content"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "new_content")

    def test_large_offset_between_hunks(self):
        """Test hunks with large gaps."""
        original = "\n".join([f"line{i}" for i in range(1, 51)])
        diff = (
            "@@ -1,1 +1,2 @@\n"
            " line1\n+inserted1\n"
            "@@ -50,1 +51,2 @@\n"
            " line50\n+inserted50"
        )
        result = apply_patch(original, diff)
        self.assertIn("inserted1", result)
        self.assertIn("inserted50", result)

    def test_fuzzy_match_offset(self):
        """Test fuzzy matching with offset."""
        original = "a\nb\nxxx\nd"
        diff = (
            "@@ -2,1 +2,2 @@\n"
            " b\n+inserted"
        )
        result = apply_patch(original, diff)
        self.assertIn("inserted", result)

    def test_delete_everything(self):
        """Test deleting all content."""
        original = "line1\nline2\nline3"
        diff = (
            "@@ -1,3 +0,0 @@\n"
            "-line1\n-line2\n-line3"
        )
        result = apply_patch(original, diff)
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
