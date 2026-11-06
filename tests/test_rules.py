"""Tests for MDFS rules loading (.mdfs/rules/ with minimal frontmatter)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mdfs.core.rules import load_rules, parse_frontmatter, render_rules


class TestParseFrontmatter(unittest.TestCase):
    """Tests for minimal frontmatter parsing."""

    def test_no_frontmatter(self):
        meta, body = parse_frontmatter("# Just a rule\n- item")
        self.assertEqual(meta, {})
        self.assertEqual(body, "# Just a rule\n- item")

    def test_frontmatter_with_priority(self):
        text = "---\npriority: 100\n---\n# Body"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["priority"], "100")
        self.assertEqual(body, "# Body")

    def test_frontmatter_with_always_apply_false(self):
        text = "---\nalwaysApply: false\n---\nBody"
        meta, _ = parse_frontmatter(text)
        self.assertEqual(meta["alwaysApply"], "false")

    def test_frontmatter_inline_comments_stripped(self):
        text = "---\npriority: 50  # high priority\n---\nBody"
        meta, _ = parse_frontmatter(text)
        self.assertEqual(meta["priority"], "50")

    def test_frontmatter_quotes_stripped(self):
        text = "---\nalwaysApply: 'no'\n---\nBody"
        meta, _ = parse_frontmatter(text)
        self.assertEqual(meta["alwaysApply"], "no")

    def test_frontmatter_without_closing_marker(self):
        text = "---\npriority: 10\n# Body without closing marker"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_frontmatter_multiline_body_preserved(self):
        text = "---\npriority: 1\n---\n# Title\n\n- line one\n- line two"
        _, body = parse_frontmatter(text)
        self.assertEqual(body, "# Title\n\n- line one\n- line two")


class TestLoadRules(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        self.rules = self.root / ".mdfs" / "rules"
        self.rules.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_rules_dir(self):
        empty_root = self.root / "nothing"
        empty_root.mkdir()
        self.assertEqual(load_rules(empty_root), [])

    def test_files_in_filesystem_order(self):
        (self.rules / "z_last.md").write_text("Last", encoding="utf-8")
        (self.rules / "a_first.md").write_text("First", encoding="utf-8")
        (self.rules / "m_middle.md").write_text("Middle", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual([r.name for r in result],
                         ["a_first.md", "m_middle.md", "z_last.md"])

    def test_priority_overrides_filesystem_order(self):
        (self.rules / "a_first.md").write_text(
            "---\npriority: 10\n---\nFirst", encoding="utf-8")
        (self.rules / "z_last.md").write_text(
            "---\npriority: 20\n---\nLast", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual([r.name for r in result], ["z_last.md", "a_first.md"])

    def test_equal_priority_keeps_filename_order(self):
        (self.rules / "b_second.md").write_text(
            "---\npriority: 5\n---\nB", encoding="utf-8")
        (self.rules / "a_first.md").write_text(
            "---\npriority: 5\n---\nA", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual([r.name for r in result], ["a_first.md", "b_second.md"])

    def test_always_apply_false_excluded_by_default(self):
        (self.rules / "always.md").write_text("Always", encoding="utf-8")
        (self.rules / "optional.md").write_text(
            "---\nalwaysApply: false\n---\nOptional", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual([r.name for r in result], ["always.md"])

    def test_include_all_includes_optional_rules(self):
        (self.rules / "always.md").write_text("Always", encoding="utf-8")
        (self.rules / "optional.md").write_text(
            "---\nalwaysApply: false\n---\nOptional", encoding="utf-8")
        result = load_rules(self.root, include_all=True)
        self.assertEqual([r.name for r in result], ["always.md", "optional.md"])

    def test_no_frontmatter_means_always_applied(self):
        (self.rules / "plain.md").write_text("Plain rule", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].always_apply)
        self.assertEqual(result[0].priority, 0)

    def test_frontmatter_stripped_from_body(self):
        (self.rules / "meta.md").write_text(
            "---\npriority: 3\nalwaysApply: true\n---\n# Real content\n- item",
            encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual(result[0].body, "# Real content\n- item")

    def test_empty_files_skipped(self):
        (self.rules / "empty.md").write_text("", encoding="utf-8")
        (self.rules / "whitespace.md").write_text("   \n  \n", encoding="utf-8")
        (self.rules / "only_frontmatter.md").write_text(
            "---\npriority: 1\n---\n", encoding="utf-8")
        self.assertEqual(load_rules(self.root), [])

    def test_non_md_files_ignored(self):
        (self.rules / "notes.txt").write_text("Not a rule", encoding="utf-8")
        self.assertEqual(load_rules(self.root), [])

    def test_invalid_priority_treated_as_zero(self):
        (self.rules / "bad.md").write_text(
            "---\npriority: high\n---\nBody", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual(result[0].priority, 0)

    def test_negative_priority_goes_last(self):
        (self.rules / "late.md").write_text(
            "---\npriority: -5\n---\nLate", encoding="utf-8")
        (self.rules / "normal.md").write_text("Normal", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual([r.name for r in result], ["normal.md", "late.md"])


class TestRenderRules(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        self.rules = self.root / ".mdfs" / "rules"
        self.rules.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_render_joins_with_blank_lines(self):
        (self.rules / "one.md").write_text("Rule one", encoding="utf-8")
        (self.rules / "two.md").write_text("Rule two", encoding="utf-8")
        result = render_rules(self.root)
        self.assertEqual(result, "Rule one\n\nRule two")

    def test_render_empty_when_no_rules(self):
        self.assertEqual(render_rules(self.root), "")

    def test_render_respects_include_all(self):
        (self.rules / "optional.md").write_text(
            "---\nalwaysApply: false\n---\nOptional", encoding="utf-8")
        self.assertEqual(render_rules(self.root), "")
        self.assertEqual(render_rules(self.root, include_all=True), "Optional")

    def test_render_strips_frontmatter(self):
        (self.rules / "meta.md").write_text(
            "---\npriority: 9\n---\nBody here", encoding="utf-8")
        self.assertEqual(render_rules(self.root), "Body here")


if __name__ == "__main__":
    unittest.main()
