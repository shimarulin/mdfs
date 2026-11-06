"""Tests for MDFS bundler."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mdfs.core.bundler import (
    RULES_END_MARKER,
    RULES_START_MARKER,
    bundle,
    _detect_max_fence,
    _lang_for_ext,
)
from mdfs.core.rules import resolve_rules


class TestDetectMaxFence(unittest.TestCase):
    """Tests for _detect_max_fence helper function."""

    def test_no_fence(self):
        """Test content without any fence markers."""
        self.assertEqual(_detect_max_fence("hello\nworld"), 0)

    def test_single_fence_3_backticks(self):
        """Test single fence with 3 backticks."""
        content = "```\ncode\n```"
        self.assertEqual(_detect_max_fence(content), 3)

    def test_single_fence_5_backticks(self):
        """Test single fence with 5 backticks."""
        content = "`````\ncode\n`````"
        self.assertEqual(_detect_max_fence(content), 5)

    def test_multiple_fences_different_lengths(self):
        """Test multiple fences with different lengths."""
        content = "```\ncode1\n```\n\n`````\ncode2\n`````"
        self.assertEqual(_detect_max_fence(content), 5)

    def test_nested_fences(self):
        """Test nested fence markers."""
        content = "````\n```\ninner\n```\n````"
        self.assertEqual(_detect_max_fence(content), 4)

    def test_fence_inline_ignored(self):
        """Test that inline backticks are ignored."""
        content = "`inline` code\n```\nblock\n```"
        self.assertEqual(_detect_max_fence(content), 3)

    def test_multiline_regex(self):
        """Test MULTILINE flag works correctly."""
        content = "line1\n```\nline3\n`````\nline5"
        self.assertEqual(_detect_max_fence(content), 5)


class TestLangForExt(unittest.TestCase):
    """Tests for _lang_for_ext helper function."""

    def test_python(self):
        self.assertEqual(_lang_for_ext("main.py"), "python")

    def test_javascript(self):
        self.assertEqual(_lang_for_ext("app.js"), "javascript")

    def test_typescript(self):
        self.assertEqual(_lang_for_ext("types.ts"), "typescript")

    def test_bash(self):
        self.assertEqual(_lang_for_ext("script.sh"), "bash")
        self.assertEqual(_lang_for_ext("script.bash"), "bash")

    def test_zsh(self):
        self.assertEqual(_lang_for_ext("config.zsh"), "zsh")

    def test_ruby(self):
        self.assertEqual(_lang_for_ext("script.rb"), "ruby")

    def test_rust(self):
        self.assertEqual(_lang_for_ext("main.rs"), "rust")

    def test_go(self):
        self.assertEqual(_lang_for_ext("main.go"), "go")

    def test_java(self):
        self.assertEqual(_lang_for_ext("Main.java"), "java")

    def test_c(self):
        self.assertEqual(_lang_for_ext("main.c"), "c")

    def test_cpp(self):
        self.assertEqual(_lang_for_ext("main.cpp"), "cpp")

    def test_css(self):
        self.assertEqual(_lang_for_ext("style.css"), "css")

    def test_html(self):
        self.assertEqual(_lang_for_ext("index.html"), "html")

    def test_xml(self):
        self.assertEqual(_lang_for_ext("config.xml"), "xml")

    def test_json(self):
        self.assertEqual(_lang_for_ext("data.json"), "json")

    def test_yaml(self):
        self.assertEqual(_lang_for_ext("config.yaml"), "yaml")
        self.assertEqual(_lang_for_ext("config.yml"), "yaml")

    def test_toml(self):
        self.assertEqual(_lang_for_ext("pyproject.toml"), "toml")

    def test_sql(self):
        self.assertEqual(_lang_for_ext("query.sql"), "sql")

    def test_markdown(self):
        self.assertEqual(_lang_for_ext("README.md"), "markdown")

    def test_text(self):
        self.assertEqual(_lang_for_ext("notes.txt"), "text")

    def test_makefile(self):
        self.assertEqual(_lang_for_ext("Makefile"), "makefile")

    def test_dockerfile(self):
        self.assertEqual(_lang_for_ext("Dockerfile"), "dockerfile")

    def test_unknown_extension(self):
        self.assertEqual(_lang_for_ext("file.unknown"), "text")

    def test_case_insensitive(self):
        self.assertEqual(_lang_for_ext("Main.PY"), "python")
        self.assertEqual(_lang_for_ext("Script.SH"), "bash")

    def test_no_extension(self):
        self.assertEqual(_lang_for_ext("Makefile"), "makefile")
        self.assertEqual(_lang_for_ext("Dockerfile"), "dockerfile")

    def test_special_extensions(self):
        self.assertEqual(_lang_for_ext("Dockerfile"), "dockerfile")
        self.assertEqual(_lang_for_ext("Makefile"), "makefile")

    def test_ini(self):
        self.assertEqual(_lang_for_ext("config.ini"), "ini")
        self.assertEqual(_lang_for_ext("config.cfg"), "ini")


class TestBundle(unittest.TestCase):

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        src = Path(self.tmpdir) / "src"
        src.mkdir()
        (src / "main.py").write_text("print('hello')\n", encoding="utf-8")
        (src / "utils.py").write_text("def helper():\n    pass\n", encoding="utf-8")

    def test_basic_bundle(self):
        result = bundle(self.tmpdir, ["src/main.py", "src/utils.py"])
        self.assertIn("<!-- file: \"src/main.py\" -->", result)
        self.assertIn("<!-- file: \"src/utils.py\" -->", result)
        self.assertIn("print('hello')", result)

    def test_missing_file(self):
        # Test with respect_gitignore=False since nonexistent file won't be expanded anyway
        result = bundle(self.tmpdir, ["nonexistent.py"], include_preamble=False, respect_gitignore=False)
        # With no files to bundle, result might be empty or minimal
        # The key is that it should not crash
        self.assertIsInstance(result, str)

    def test_nested_fences_get_longer_fence(self):
        md_file = Path(self.tmpdir) / "doc.md"
        md_file.write_text("# Doc\n\n```python\nprint(1)\n```\n", encoding="utf-8")
        result = bundle(self.tmpdir, ["doc.md"])
        self.assertIn("````", result)

    def test_empty_file_list(self):
        """Empty file list produces a rules-only document (no file sections)."""
        result = bundle(self.tmpdir, [], rules="My rule")
        self.assertIsInstance(result, str)
        self.assertIn(RULES_START_MARKER, result)
        self.assertIn(RULES_END_MARKER, result)
        self.assertNotIn("print('hello')", result)
        self.assertNotIn("## Содержание", result)
        self.assertNotIn("Now process the following document", result)

    def test_heading_level_1(self):
        result = bundle(self.tmpdir, ["src/main.py"], heading_level=1)
        self.assertIn("# `src/main.py`", result)
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_heading_level_2(self):
        result = bundle(self.tmpdir, ["src/main.py"], heading_level=2)
        self.assertIn("## `src/main.py`", result)
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_heading_level_4(self):
        result = bundle(self.tmpdir, ["src/main.py"], heading_level=4)
        self.assertIn("#### `src/main.py`", result)
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_file_without_trailing_newline(self):
        no_newline = Path(self.tmpdir) / "nonewline.py"
        no_newline.write_text("code", encoding="utf-8")
        result = bundle(self.tmpdir, ["nonewline.py"])
        self.assertIn("```python\ncode\n```", result)

    def test_file_with_trailing_newline(self):
        with_newline = Path(self.tmpdir) / "withnewline.py"
        with_newline.write_text("code\n", encoding="utf-8")
        result = bundle(self.tmpdir, ["withnewline.py"])
        # Newline should be stripped once
        lines = result.split("```python\n")[1].split("\n```")[0].split("\n")
        self.assertEqual(lines[-1], "code")

    def test_multiple_files_in_bundle(self):
        result = bundle(self.tmpdir, ["src/main.py", "src/utils.py"], include_preamble=False)
        lines = result.split("\n")
        # Both files should have file markers
        file_markers = [l for l in lines if "<!-- file: \"" in l]
        self.assertEqual(len(file_markers), 2)

    def test_content_with_internal_fences(self):
        fenced = Path(self.tmpdir) / "fenced.md"
        fenced.write_text("# Doc\n\n```bash\necho hello\n```\n\nMore text", encoding="utf-8")
        result = bundle(self.tmpdir, ["fenced.md"])
        # Should use longer fence (````) since file has 3-backtick fence
        self.assertIn("````markdown", result)

    def test_base_dir_as_string(self):
        result = bundle(str(self.tmpdir), ["src/main.py"])
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_base_dir_as_path(self):
        result = bundle(Path(self.tmpdir), ["src/main.py"])
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_html_file(self):
        html = Path(self.tmpdir) / "index.html"
        html.write_text("<h1>Hello</h1>\n", encoding="utf-8")
        result = bundle(self.tmpdir, ["index.html"])
        self.assertIn("```html", result)

    def test_json_file(self):
        json_file = Path(self.tmpdir) / "config.json"
        json_file.write_text('{"key": "value"}\n', encoding="utf-8")
        result = bundle(self.tmpdir, ["config.json"])
        self.assertIn("```json", result)

    def test_include_preamble_true(self):
        """Test bundle with preamble enabled (default)."""
        result = bundle(self.tmpdir, ["src/main.py"], include_preamble=True,
                        rules="My rule")
        self.assertIn("MANDATORY FORMAT RULES", result)
        self.assertIn(RULES_START_MARKER, result)
        self.assertIn(RULES_END_MARKER, result)
        self.assertIn("QUICK REMINDER", result)
        self.assertIn("## Содержание", result)
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_include_preamble_false(self):
        """Test bundle with preamble disabled."""
        result = bundle(self.tmpdir, ["src/main.py"], include_preamble=False)
        self.assertNotIn("MANDATORY FORMAT RULES", result)
        self.assertNotIn(RULES_START_MARKER, result)
        self.assertNotIn("QUICK REMINDER", result)
        self.assertNotIn("## Содержание", result)
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_preamble_with_multiple_files(self):
        """Test that quick reminder appears before each file."""
        result = bundle(self.tmpdir, ["src/main.py", "src/utils.py"], include_preamble=True)
        # Count occurrences of QUICK REMINDER
        reminder_count = result.count("QUICK REMINDER")
        # Should appear once at the beginning and once before each file (2 files = 2 more)
        self.assertEqual(reminder_count, 2)

    def test_table_of_contents_generation(self):
        """Test that table of contents is generated correctly."""
        result = bundle(self.tmpdir, ["src/main.py", "src/utils.py"], include_preamble=True)
        self.assertIn("## Содержание", result)
        self.assertIn("- [src/main.py]", result)
        self.assertIn("- [src/utils.py]", result)

    def test_preamble_default_enabled(self):
        """Test that preamble is enabled by default."""
        result = bundle(self.tmpdir, ["src/main.py"])
        self.assertIn("MANDATORY FORMAT RULES", result)
        self.assertIn("QUICK REMINDER", result)

    # ----- rules from .mdfs/rules/ -----

    def test_rules_included_in_full_bundle(self):
        """Rules text is inserted inside the mdfs:rules block."""
        result = bundle(self.tmpdir, ["src/main.py"], rules="My custom rule")
        rules_start = result.find(RULES_START_MARKER)
        rules_end = result.find(RULES_END_MARKER)
        self.assertTrue(0 < rules_start < rules_end)
        block = result[rules_start:rules_end]
        self.assertIn("My custom rule", block)
        self.assertIn("MANDATORY FORMAT RULES", result)

    def test_rules_block_markers_and_rule_framing(self):
        """Rules block uses mdfs:rules markers; every rule is framed."""
        rules_dir = Path(self.tmpdir) / ".mdfs" / "rules"
        rules_dir.mkdir(parents=True)
        (rules_dir / "rule.md").write_text("My custom rule", encoding="utf-8")
        result = bundle(
            self.tmpdir, ["src/main.py"],
            rules=resolve_rules(rules_dir, ["*"]),
        )
        self.assertIn(RULES_START_MARKER, result)
        self.assertIn(RULES_END_MARKER, result)
        # Project rules are framed with their file name
        self.assertIn('<!-- mdfs:rule:start name="rule.md" -->', result)
        self.assertIn('<!-- mdfs:rule:end name="rule.md" -->', result)

    def test_no_rules_no_builtin_prompt(self):
        """Without rules the built-in prompt is not embedded in the bundle."""
        result = bundle(self.tmpdir, ["src/main.py"], rules=None)
        self.assertNotIn(RULES_START_MARKER, result)
        self.assertNotIn("# Rule: File Output Format", result)
        # Preamble and document flow are intact
        self.assertIn("MANDATORY FORMAT RULES", result)
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_rules_empty_not_added(self):
        """Empty/whitespace rules text does not add a blank section."""
        with_rules = bundle(self.tmpdir, ["src/main.py"], rules="   ")
        without_rules = bundle(self.tmpdir, ["src/main.py"], rules=None)
        self.assertEqual(with_rules, without_rules)

    # ----- rules-only mode (no files) -----

    def test_rules_only_mode(self):
        """No files: rules-only document without TOC and file sections."""
        result = bundle(self.tmpdir, [], rules="Rule A\n\nRule B")
        self.assertIn(RULES_START_MARKER, result)
        self.assertIn(RULES_END_MARKER, result)
        self.assertIn("Rule A\n\nRule B", result)
        self.assertIn("apply to the entire conversation", result)
        self.assertNotIn("## Содержание", result)
        self.assertNotIn("print('hello')", result)
        self.assertNotIn("QUICK REMINDER", result)
        self.assertNotIn("Now process the following document", result)

    def test_rules_only_mode_without_rules(self):
        """Rules-only mode without any rules: preamble only, no rules block."""
        result = bundle(self.tmpdir, [])
        self.assertNotIn(RULES_START_MARKER, result)
        self.assertNotIn(RULES_END_MARKER, result)
        self.assertIn("MANDATORY FORMAT RULES", result)

    # ----- question section -----

    def test_question_in_rules_only_mode(self):
        """--query in rules-only mode appends the Question section."""
        result = bundle(self.tmpdir, [], rules="Rule A",
                        query="What is this project?")
        self.assertIn("<!-- question -->", result)
        self.assertIn("## Question", result)
        self.assertIn("What is this project?", result)
        # Question goes after the rules block
        self.assertGreater(
            result.find("## Question"), result.find(RULES_END_MARKER))

    def test_question_in_full_bundle(self):
        """--query with files appends the Question after the file sections."""
        result = bundle(self.tmpdir, ["src/main.py"], query="Review this code")
        self.assertIn("## Question", result)
        self.assertIn("Review this code", result)
        self.assertGreater(
            result.find("## Question"), result.find('<!-- file: "src/main.py" -->'))

    def test_question_marker_not_parsed_as_file(self):
        """A question-only document must yield no extractable blocks."""
        from mdfs.core.parser import parse
        doc = "---\n\n<!-- question -->\n## Question\n\nWhy?\n"
        self.assertEqual(parse(doc), [])

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
