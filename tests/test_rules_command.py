"""Tests for the RulesCommand (deprecated alias of the rules-only bundle)."""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import patch

import pytest

from mdfs.commands.rules import RulesCommand
from mdfs.core.bundler import RULES_END_MARKER, RULES_START_MARKER
from mdfs.default_system_prompt import DEFAULT_SYSTEM_PROMPT


def make_cmd() -> RulesCommand:
    """Build a RulesCommand with a minimal args namespace."""
    return RulesCommand(Namespace())


class TestRulesCommandInitialization:
    """Tests for RulesCommand initialization."""

    def test_init_sets_args(self):
        """RulesCommand stores arguments."""
        args = Namespace()
        cmd = RulesCommand(args)
        assert cmd.args is args

    def test_init_does_not_require_mdfs_root(self):
        """RulesCommand init works even without .mdfs (root falls back to cwd)."""
        cmd = make_cmd()
        assert cmd is not None


class TestRulesCommandExecute:
    """Tests for RulesCommand.execute() — deprecated rules-only bundle."""

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_execute_prints_rules_document(self, mock_copy, capsys):
        """execute() prints the rules-only bundle document to stdout."""
        exit_code = make_cmd().execute()

        captured = capsys.readouterr()
        assert exit_code == 0
        # Preamble and the rules block envelope are present
        assert "MANDATORY FORMAT RULES" in captured.out
        assert RULES_START_MARKER in captured.out
        assert RULES_END_MARKER in captured.out
        # The file output format rule body is inside the rules block
        assert "# Rule: File Output Format" in captured.out

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_execute_warns_about_deprecation(self, mock_copy, capsys):
        """execute() prints a deprecation notice to stderr."""
        make_cmd().execute()

        captured = capsys.readouterr()
        assert "deprecated" in captured.err
        assert "mdfs bundle" in captured.err

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_execute_copies_document_to_clipboard(self, mock_copy, capsys):
        """execute() copies the same document it prints."""
        make_cmd().execute()

        captured = capsys.readouterr()
        copied = mock_copy.call_args[0][0]
        assert copied.strip() == captured.out.strip()
        assert "# Rule: File Output Format" in copied

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_execute_returns_zero(self, mock_copy):
        """execute() returns exit code 0 on success."""
        assert make_cmd().execute() == 0

    def test_execute_prints_document_before_clipboard_error(self, capsys):
        """The document is printed even if clipboard copying fails."""
        with patch(
            "mdfs.commands.rules.copy_to_clipboard", side_effect=SystemExit(1)
        ):
            with pytest.raises(SystemExit):
                make_cmd().execute()

        captured = capsys.readouterr()
        assert "# Rule: File Output Format" in captured.out


class TestRulesCommandSelection:
    """Rules selection: the alias honors the same globs as bundle."""

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_uses_config_rules_always(self, mock_copy, tmp_path, monkeypatch,
                                      capsys):
        """rules_always globs from .mdfsrc.yaml select the rules."""
        (tmp_path / ".mdfsrc.yaml").write_text(
            'rules_dir: "rules"\nrules_always:\n  - "10-*"\n',
            encoding="utf-8",
        )
        rdir = tmp_path / "rules"
        rdir.mkdir()
        (rdir / "10-style.md").write_text("# Style rule body\n", encoding="utf-8")

        monkeypatch.chdir(tmp_path)
        make_cmd().execute()

        out = capsys.readouterr().out
        assert 'name="10-style.md"' in out
        # Packaged fallback for the file output format rule is guaranteed
        assert "default-file-output-format" in out


class TestRulesCommandContent:
    """Tests for the content of the system prompt."""

    def test_default_system_prompt_contains_markers(self):
        """DEFAULT_SYSTEM_PROMPT contains marker examples."""
        assert "<!-- file:" in DEFAULT_SYSTEM_PROMPT
        assert "<!-- patch:" in DEFAULT_SYSTEM_PROMPT

    def test_default_system_prompt_contains_requirements(self):
        """DEFAULT_SYSTEM_PROMPT contains Requirements section."""
        assert "## Requirements" in DEFAULT_SYSTEM_PROMPT

    def test_default_system_prompt_contains_compliance(self):
        """DEFAULT_SYSTEM_PROMPT contains Compliance checklist."""
        assert "compliance" in DEFAULT_SYSTEM_PROMPT.lower()


class TestRulesCommandClipboard:
    """Tests for clipboard functionality in RulesCommand."""

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_clipboard_copy_called_with_document(self, mock_copy):
        """copy_to_clipboard is called with the rules-only document."""
        make_cmd().execute()
        copied = mock_copy.call_args[0][0]
        assert RULES_START_MARKER in copied
        assert "default-system-prompt" not in copied  # old builtin block is gone

    def test_clipboard_copy_error_propagates(self):
        """SystemExit from copy_to_clipboard is re-raised."""
        with patch(
            "mdfs.commands.rules.copy_to_clipboard", side_effect=SystemExit(1)
        ):
            with pytest.raises(SystemExit):
                make_cmd().execute()

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_execute_order_print_before_copy(self, mock_copy, capsys):
        """execute() prints to stdout before attempting clipboard copy."""
        copied_state = {}

        def track_copy(text):
            captured = capsys.readouterr()
            copied_state["out_len"] = len(captured.out)
            assert "# Rule:" in captured.out

        mock_copy.side_effect = track_copy
        make_cmd().execute()
        assert copied_state["out_len"] > 100


class TestRulesCommandIntegration:
    """Integration tests for RulesCommand."""

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_rules_command_full_flow(self, mock_copy, capsys):
        """Full flow: deprecation notice, print, copy, confirm."""
        exit_code = make_cmd().execute()

        assert exit_code == 0
        captured = capsys.readouterr()
        assert "# Rule: File Output Format" in captured.out
        assert "deprecated" in captured.err
        assert "✅" in captured.err
        assert "Copied to clipboard" in captured.err
        assert mock_copy.called

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_rules_command_multiple_executions(self, mock_copy, capsys):
        """RulesCommand can be executed multiple times."""
        for _ in range(3):
            assert make_cmd().execute() == 0

        captured = capsys.readouterr()
        assert captured.err.count("✅") == 3
        assert captured.err.count("deprecated") == 3

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_rules_command_with_different_args(self, mock_copy, capsys):
        """RulesCommand works with any Namespace args."""
        args = Namespace(
            dir=".",
            command="rules",
            verbose=False,
            extra_field="extra_value",
        )

        with patch("mdfs.commands.rules.copy_to_clipboard"):
            assert RulesCommand(args).execute() == 0

        captured = capsys.readouterr()
        assert "# Rule:" in captured.out


class TestRulesCommandErrorScenarios:
    """Tests for error scenarios in RulesCommand."""

    def test_execute_handles_clipboard_unavailable(self, capsys):
        """execute() handles unavailable clipboard gracefully."""
        with patch(
            "mdfs.commands.rules.copy_to_clipboard", side_effect=SystemExit(1)
        ):
            with pytest.raises(SystemExit):
                make_cmd().execute()

        captured = capsys.readouterr()
        assert "# Rule:" in captured.out

    def test_execute_handles_unexpected_error(self, capsys):
        """execute() handles unexpected errors in copy_to_clipboard."""
        with patch(
            "mdfs.commands.rules.copy_to_clipboard",
            side_effect=RuntimeError("unexpected error"),
        ):
            with pytest.raises(RuntimeError):
                make_cmd().execute()

        captured = capsys.readouterr()
        assert "# Rule:" in captured.out


class TestRulesCommandOutput:
    """Tests for output formatting in RulesCommand."""

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_output_to_stdout(self, mock_copy, capsys):
        """Document goes to stdout, notices stay on stderr."""
        make_cmd().execute()

        captured = capsys.readouterr()
        assert "# Rule:" in captured.out
        assert "# Rule:" not in captured.err
        assert "deprecated" not in captured.out

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_success_message_to_stderr(self, mock_copy, capsys):
        """Success message is printed to stderr."""
        make_cmd().execute()

        captured = capsys.readouterr()
        assert "✅" in captured.err
        assert "✅" not in captured.out

    @patch("mdfs.commands.rules.copy_to_clipboard")
    def test_output_not_mixed(self, mock_copy, capsys):
        """stdout and stderr outputs are properly separated."""
        make_cmd().execute()

        captured = capsys.readouterr()
        assert len(captured.out) > 100
        assert "Copied to clipboard" in captured.err


class TestRulesCommandPromptContent:
    """Tests to verify prompt content is complete and correct."""

    def test_prompt_has_required_sections(self):
        """DEFAULT_SYSTEM_PROMPT has all required sections."""
        required_sections = [
            "# Rule: File Output Format",
            "## Requirements",
            "### Markers",
            "### Fence depth",
            "### Choosing between file and patch",
            "## Compliance checklist",
        ]

        for section in required_sections:
            assert section in DEFAULT_SYSTEM_PROMPT, f"Missing section: {section}"

    def test_prompt_has_code_examples(self):
        """DEFAULT_SYSTEM_PROMPT includes code examples."""
        assert "```markdown" in DEFAULT_SYSTEM_PROMPT
        assert "```diff" in DEFAULT_SYSTEM_PROMPT
        assert "```lang" in DEFAULT_SYSTEM_PROMPT

    def test_prompt_has_table(self):
        """DEFAULT_SYSTEM_PROMPT includes markdown tables."""
        assert "|" in DEFAULT_SYSTEM_PROMPT
        assert "---|" in DEFAULT_SYSTEM_PROMPT or "|---" in DEFAULT_SYSTEM_PROMPT
