"""Tests for filename generation and label sanitization."""

import unittest
from mdfs.utils import sanitize_label, make_filename


class TestSanitizeLabel(unittest.TestCase):

    def test_simple(self):
        self.assertEqual(sanitize_label("hello world"), "hello_world")

    def test_special_chars(self):
        self.assertEqual(sanitize_label("fix: bug #123!"), "fix_bug_123")

    def test_unicode(self):
        result = sanitize_label("добавить CLI")
        self.assertEqual(result, "добавить_cli")

    def test_multiple_spaces(self):
        self.assertEqual(sanitize_label("a   b   c"), "a_b_c")

    def test_empty(self):
        self.assertEqual(sanitize_label(""), "")

    def test_only_special(self):
        self.assertEqual(sanitize_label("!!!"), "")

    def test_slashes(self):
        self.assertEqual(sanitize_label("src/main.py changes"), "srcmainpy_changes")


class TestMakeFilename(unittest.TestCase):

    def test_with_label(self):
        name = make_filename("add CLI")
        self.assertRegex(name, r"\d{4}-\d{2}-\d{2}_\d{6}__add_cli\.md")

    def test_without_label(self):
        name = make_filename(None)
        self.assertRegex(name, r"\d{4}-\d{2}-\d{2}_\d{6}\.md")

    def test_empty_label(self):
        name = make_filename("")
        self.assertRegex(name, r"\d{4}-\d{2}-\d{2}_\d{6}\.md")

    def test_label_all_special(self):
        name = make_filename("!!!")
        self.assertRegex(name, r"\d{4}-\d{2}-\d{2}_\d{6}\.md")


if __name__ == "__main__":
    unittest.main()
