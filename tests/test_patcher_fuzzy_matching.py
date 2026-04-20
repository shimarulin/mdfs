"""Tests for improved fuzzy matching in MDFS patcher."""

import unittest
from mdfs.core.patcher import _find_match


class TestPatcherFuzzyMatching(unittest.TestCase):

    def test_exact_match_at_hint(self):
        """Test that exact match at hint position works."""
        file_lines = ["line1", "line2", "line3", "line4", "line5"]
        pattern = ["line2", "line3"]
        result = _find_match(file_lines, pattern, 2)
        self.assertEqual(result, 1)  # 0-indexed position

    def test_expanding_search_from_hint(self):
        """Test that search expands outward from hint position."""
        file_lines = ["line1", "line2", "line3", "line4", "line5"]
        pattern = ["line4", "line5"]
        # Hint is at position 1, but match is at position 3
        result = _find_match(file_lines, pattern, 2)
        self.assertEqual(result, 3)

    def test_stripped_whitespace_matching(self):
        """Test matching with whitespace differences."""
        file_lines = ["line1  ", "  line2", "line3\t", "line4"]
        pattern = ["line1", "line2", "line3"]
        result = _find_match(file_lines, pattern, 1)
        self.assertIsNotNone(result)

    def test_strip_matching(self):
        """Test matching with leading/trailing whitespace stripped."""
        file_lines = ["  line1  ", "\tline2\t", "  line3  ", "line4"]
        pattern = ["line1", "line2", "line3"]
        result = _find_match(file_lines, pattern, 1)
        self.assertIsNotNone(result)

    def test_fuzzy_matching_with_partial_matches(self):
        """Test fuzzy matching with partial matches."""
        file_lines = ["line1", "different_line", "line3", "line4", "changed_line"]
        pattern = ["line1", "line2", "line3"]  # line2 doesn't exactly match
        result = _find_match(file_lines, pattern, 1)
        # With our improved algorithm, this should now find a match
        self.assertIsNotNone(result)

    def test_no_match_when_below_threshold(self):
        """Test that no match is found when below threshold."""
        file_lines = ["line1", "completely_different", "another_different", "line4"]
        pattern = ["line1", "line2", "line3"]
        result = _find_match(file_lines, pattern, 1)
        # Should not find a match because only 1 out of 3 lines match (33% < 70% threshold)
        self.assertIsNone(result)

    def test_single_line_pattern_match(self):
        """Test that single line patterns match even with low percentage."""
        file_lines = ["line1", "completely_different", "line3"]
        pattern = ["line3"]
        result = _find_match(file_lines, pattern, 1)
        # Should find a match for the single line even though it's not near the hint
        self.assertIsNotNone(result)

    def test_empty_pattern(self):
        """Test handling of empty pattern."""
        file_lines = ["line1", "line2", "line3"]
        pattern = []
        result = _find_match(file_lines, pattern, 5)
        self.assertEqual(result, 4)  # max(0, hint_start - 1) = max(0, 4) = 4


if __name__ == "__main__":
    unittest.main()
