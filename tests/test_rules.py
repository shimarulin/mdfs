"""Tests for MDFS rules loading (.mdfs/rules/ with minimal frontmatter)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mdfs.core.rules import (
    Rule,
    load_rules,
    parse_frontmatter,
    render_rule,
    render_rules,
)


class TestParseFrontmatter(unittest.TestCase):
    """Tests for minimal frontmatter parsing."""

    def test_no_frontmatter(self):
        meta, body = parse_frontmatter("# Just a rule\n- item")
        self.assertEqual(meta, {})
        self.assertEqual(body, "# Just a rule\n- item")

    def test_frontmatter_with_scalar(self):
        text = "---\nalwaysApply: true\n---\n# Body"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta["alwaysApply"], "true")
        self.assertEqual(body, "# Body")

    def test_frontmatter_with_always_apply_false(self):
        text = "---\nalwaysApply: false\n---\nBody"
        meta, _ = parse_frontmatter(text)
        self.assertEqual(meta["alwaysApply"], "false")

    def test_frontmatter_inline_comments_stripped(self):
        text = "---\nalwaysApply: true  # always on\n---\nBody"
        meta, _ = parse_frontmatter(text)
        self.assertEqual(meta["alwaysApply"], "true")

    def test_frontmatter_quotes_stripped(self):
        text = "---\nalwaysApply: 'no'\n---\nBody"
        meta, _ = parse_frontmatter(text)
        self.assertEqual(meta["alwaysApply"], "no")

    def test_frontmatter_without_closing_marker(self):
        text = "---\nalwaysApply: true\n# Body without closing marker"
        meta, body = parse_frontmatter(text)
        self.assertEqual(meta, {})
        self.assertEqual(body, text)

    def test_frontmatter_multiline_body_preserved(self):
        text = "---\nalwaysApply: true\n---\n# Title\n\n- line one\n- line two"
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

    def test_numeric_prefixes_control_order(self):
        (self.rules / "90-last.md").write_text("Late", encoding="utf-8")
        (self.rules / "00-first.md").write_text("Early", encoding="utf-8")
        (self.rules / "10-middle.md").write_text("Middle", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual([r.name for r in result],
                         ["00-first.md", "10-middle.md", "90-last.md"])

    def test_prefixes_sort_before_plain_names(self):
        (self.rules / "notes.md").write_text("Notes", encoding="utf-8")
        (self.rules / "00-first.md").write_text("Early", encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual([r.name for r in result],
                         ["00-first.md", "notes.md"])

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

    def test_frontmatter_stripped_from_body(self):
        (self.rules / "meta.md").write_text(
            "---\nalwaysApply: true\n---\n# Real content\n- item",
            encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual(result[0].body, "# Real content\n- item")

    def test_empty_files_skipped(self):
        (self.rules / "empty.md").write_text("", encoding="utf-8")
        (self.rules / "whitespace.md").write_text("   \n  \n", encoding="utf-8")
        (self.rules / "only_frontmatter.md").write_text(
            "---\nalwaysApply: true\n---\n", encoding="utf-8")
        self.assertEqual(load_rules(self.root), [])

    def test_non_md_files_ignored(self):
        (self.rules / "notes.txt").write_text("Not a rule", encoding="utf-8")
        self.assertEqual(load_rules(self.root), [])

    def test_unknown_frontmatter_keys_ignored(self):
        (self.rules / "extra.md").write_text(
            "---\ndescription: Some rule\nversion: 2\n---\nBody",
            encoding="utf-8")
        result = load_rules(self.root)
        self.assertEqual(len(result), 1)
        self.assertTrue(result[0].always_apply)
        self.assertEqual(result[0].body, "Body")

    def test_always_apply_false_string_variants(self):
        for i, value in enumerate(("false", "no", "0", "off")):
            name = f"opt_{i}.md"
            (self.rules / name).write_text(
                f"---\nalwaysApply: {value}\n---\nOptional",
                encoding="utf-8")
            result = load_rules(self.root, include_all=True)
            self.assertFalse(result[i].always_apply, value)


class TestRenderRule(unittest.TestCase):

    def test_render_rule_wraps_body_in_markers(self):
        rule = Rule(name="10-style.md", always_apply=True, body="# Style\n- item")
        result = render_rule(rule)
        self.assertEqual(
            result,
            '<!-- mdfs:rule:start name="10-style.md" -->\n'
            "# Style\n- item\n"
            '<!-- mdfs:rule:end name="10-style.md" -->',
        )


class TestRenderRules(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.root = Path(self.tmpdir)
        self.rules = self.root / ".mdfs" / "rules"
        self.rules.mkdir(parents=True)

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_render_wraps_each_rule_in_markers(self):
        (self.rules / "one.md").write_text("Rule one", encoding="utf-8")
        (self.rules / "two.md").write_text("Rule two", encoding="utf-8")
        result = render_rules(self.root)
        self.assertEqual(
            result,
            '<!-- mdfs:rule:start name="one.md" -->\n'
            "Rule one\n"
            '<!-- mdfs:rule:end name="one.md" -->\n'
            "\n"
            '<!-- mdfs:rule:start name="two.md" -->\n'
            "Rule two\n"
            '<!-- mdfs:rule:end name="two.md" -->',
        )

    def test_render_empty_when_no_rules(self):
        self.assertEqual(render_rules(self.root), "")

    def test_render_respects_include_all(self):
        (self.rules / "optional.md").write_text(
            "---\nalwaysApply: false\n---\nOptional", encoding="utf-8")
        self.assertEqual(render_rules(self.root), "")
        self.assertIn("Optional", render_rules(self.root, include_all=True))

    def test_render_strips_frontmatter(self):
        (self.rules / "meta.md").write_text(
            "---\nalwaysApply: true\n---\nBody here", encoding="utf-8")
        result = render_rules(self.root)
        self.assertIn("\nBody here\n", result)
        self.assertNotIn("alwaysApply", result)


if __name__ == "__main__":
    unittest.main()
