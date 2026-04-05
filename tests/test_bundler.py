"""Tests for MDFS bundler."""

import shutil
import tempfile
import unittest
from pathlib import Path

from mdfs.core.bundler import bundle, _detect_max_fence, _lang_for_ext


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
        result = bundle(self.tmpdir, ["nonexistent.py"])
        self.assertIn("File not found", result)

    def test_with_system_prompt(self):
        result = bundle(self.tmpdir, ["src/main.py"], system_prompt="You are helpful.", include_preamble=False)
        self.assertIn("You are helpful.", result)
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_system_prompt_with_trailing_whitespace(self):
        result = bundle(self.tmpdir, ["src/main.py"], system_prompt="Prompt  \n  ", include_preamble=False)
        self.assertIn("Prompt", result)
        self.assertNotIn("Prompt  ", result)

    def test_nested_fences_get_longer_fence(self):
        md_file = Path(self.tmpdir) / "doc.md"
        md_file.write_text("# Doc\n\n```python\nprint(1)\n```\n", encoding="utf-8")
        result = bundle(self.tmpdir, ["doc.md"])
        self.assertIn("````", result)

    def test_empty_file_list(self):
        result = bundle(self.tmpdir, [])
        # Should return just the separator if prompt given
        self.assertIsInstance(result, str)

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

    def test_system_prompt_separator(self):
        result = bundle(self.tmpdir, ["src/main.py"], system_prompt="Prompt")
        lines = result.split("\n")
        self.assertIn("---", lines)

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
        result = bundle(self.tmpdir, ["src/main.py"], include_preamble=True)
        self.assertIn("MANDATORY FORMAT RULES", result)
        self.assertIn("--- START OF RULES ---", result)
        self.assertIn("--- END OF RULES ---", result)
        self.assertIn("QUICK REMINDER", result)
        self.assertIn("## Содержание", result)
        self.assertIn("<!-- file: \"src/main.py\" -->", result)

    def test_include_preamble_false(self):
        """Test bundle with preamble disabled."""
        result = bundle(self.tmpdir, ["src/main.py"], include_preamble=False)
        self.assertNotIn("MANDATORY FORMAT RULES", result)
        self.assertNotIn("--- START OF RULES ---", result)
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

    def tearDown(self):
        shutil.rmtree(self.tmpdir)


if __name__ == "__main__":
    unittest.main()
