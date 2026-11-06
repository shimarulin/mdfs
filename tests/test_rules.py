"""Tests for MDFS rules loading (.mdfs/rules/, glob-based selection)."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mdfs.core.rules import (
    BUILTIN_RULE_NAME,
    DEFAULT_RULE_NAME,
    Rule,
    built_in_rule,
    load_rules,
    render_rule,
    render_rules,
    resolve_rules,
)
from mdfs.default_system_prompt import DEFAULT_SYSTEM_PROMPT


def write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class TestLoadRules(unittest.TestCase):
    """Selection of rule files by filename globs."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rules = Path(self.tmpdir) / ".mdfs" / "rules"

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_rules_dir(self):
        self.assertEqual(load_rules(Path(self.tmpdir) / "nothing", ["*"]), [])

    def test_empty_patterns_select_nothing(self):
        write(self.rules / "00-format.md", "Format")
        self.assertEqual(load_rules(self.rules, []), [])

    def test_files_in_filename_order(self):
        write(self.rules / "z_last.md", "Last")
        write(self.rules / "a_first.md", "First")
        write(self.rules / "m_middle.md", "Middle")
        result = load_rules(self.rules, ["*"])
        self.assertEqual([r.name for r in result],
                         ["a_first.md", "m_middle.md", "z_last.md"])

    def test_numeric_prefixes_control_order(self):
        write(self.rules / "90-last.md", "Late")
        write(self.rules / "00-first.md", "Early")
        write(self.rules / "10-middle.md", "Middle")
        result = load_rules(self.rules, ["*"])
        self.assertEqual([r.name for r in result],
                         ["00-first.md", "10-middle.md", "90-last.md"])

    def test_default_glob_selects_only_prefix_00(self):
        write(self.rules / DEFAULT_RULE_NAME, "Format")
        write(self.rules / "10-style.md", "Style")
        result = load_rules(self.rules, ["00-*"])
        self.assertEqual([r.name for r in result], [DEFAULT_RULE_NAME])

    def test_multiple_globs_are_unioned(self):
        write(self.rules / "00-format.md", "Format")
        write(self.rules / "10-style.md", "Style")
        write(self.rules / "20-domain.md", "Domain")
        result = load_rules(self.rules, ["00-*", "1*"])
        self.assertEqual([r.name for r in result],
                         ["00-format.md", "10-style.md"])

    def test_star_glob_selects_everything(self):
        write(self.rules / "00-format.md", "Format")
        write(self.rules / "10-style.md", "Style")
        write(self.rules / "notes.md", "Notes")
        result = load_rules(self.rules, ["*"])
        self.assertEqual(len(result), 3)

    def test_no_match_selects_nothing(self):
        write(self.rules / "10-style.md", "Style")
        self.assertEqual(load_rules(self.rules, ["2*"]), [])

    def test_non_md_and_empty_files_skipped(self):
        write(self.rules / "notes.txt", "Not a rule")
        write(self.rules / "empty.md", "")
        write(self.rules / "10-style.md", "Style")
        result = load_rules(self.rules, ["*"])
        self.assertEqual([r.name for r in result], ["10-style.md"])

    def test_bodies_stripped(self):
        write(self.rules / "10-style.md", "\n  Style body  \n")
        result = load_rules(self.rules, ["*"])
        self.assertEqual(result[0].body, "Style body")


class TestBuiltInRule(unittest.TestCase):

    def test_name_and_body(self):
        rule = built_in_rule()
        self.assertEqual(rule.name, BUILTIN_RULE_NAME)
        self.assertEqual(rule.body, DEFAULT_SYSTEM_PROMPT.rstrip())

    def test_builtin_name_has_no_md_suffix(self):
        self.assertFalse(BUILTIN_RULE_NAME.endswith(".md"))


class TestRenderRule(unittest.TestCase):

    def test_render_rule_wraps_body_in_markers(self):
        rule = Rule(name="10-style.md", body="# Style\n- item")
        result = render_rule(rule)
        self.assertEqual(
            result,
            '<!-- mdfs:rule:start name="10-style.md" -->\n'
            "# Style\n- item\n"
            '<!-- mdfs:rule:end name="10-style.md" -->',
        )


class TestRenderRules(unittest.TestCase):

    def test_render_wraps_each_rule_in_markers(self):
        rules = [Rule(name="one.md", body="Rule one"),
                 Rule(name="two.md", body="Rule two")]
        result = render_rules(rules)
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

    def test_render_empty_list(self):
        self.assertEqual(render_rules([]), "")


class TestResolveRules(unittest.TestCase):
    """Built-in fallback when 00-file-output-format.md is absent."""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.rules = Path(self.tmpdir) / ".mdfs" / "rules"

    def tearDown(self):
        shutil.rmtree(self.tmpdir)

    def test_missing_dir_falls_back_to_builtin(self):
        result = resolve_rules(self.rules, ["00-*"])
        self.assertIn('name="default-file-output-format"', result)
        self.assertIn("File Output Format", result)

    def test_builtin_goes_first(self):
        write(self.rules / "10-style.md", "Style")
        result = resolve_rules(self.rules, ["1*"])
        builtin_pos = result.find("default-file-output-format")
        style_pos = result.find("name=\"10-style.md\"")
        self.assertLess(builtin_pos, style_pos)

    def test_project_file_present_no_builtin(self):
        write(self.rules / DEFAULT_RULE_NAME, "Project format rule")
        result = resolve_rules(self.rules, ["00-*"])
        self.assertIn("Project format rule", result)
        self.assertNotIn("default-file-output-format", result)

    def test_file_present_but_not_selected_no_fallback(self):
        write(self.rules / DEFAULT_RULE_NAME, "Project format rule")
        write(self.rules / "10-style.md", "Style")
        result = resolve_rules(self.rules, ["1*"])
        self.assertIn("Style", result)
        self.assertNotIn("File Output Format", result)

    def test_nothing_selected_returns_empty(self):
        write(self.rules / DEFAULT_RULE_NAME, "Project format rule")
        self.assertEqual(resolve_rules(self.rules, ["9*"]), "")

    def test_default_glob_on_project_dir(self):
        write(self.rules / DEFAULT_RULE_NAME, "Project format rule")
        write(self.rules / "10-style.md", "Style")
        result = resolve_rules(self.rules, ["00-*"])
        self.assertIn("Project format rule", result)
        self.assertNotIn("Style", result)


if __name__ == "__main__":
    unittest.main()
