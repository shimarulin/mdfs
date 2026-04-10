"""Tests for the RulesCommand."""

from __future__ import annotations

from argparse import Namespace
from unittest.mock import patch, MagicMock
from io import StringIO

import pytest

from mdfs.commands.rules import RulesCommand
from mdfs.default_system_prompt import DEFAULT_SYSTEM_PROMPT


class TestRulesCommandInitialization:
    """Tests for RulesCommand initialization."""

    def test_init_sets_args(self):
        """RulesCommand stores arguments."""
        args = Namespace()
        cmd = RulesCommand(args)
        assert cmd.args is args

    def test_init_does_not_require_mdfs_root(self):
        """RulesCommand doesn't require .mdfs directory to exist."""
        # This should not raise an error even without .mdfs
        args = Namespace()
        cmd = RulesCommand(args)
        assert cmd is not None


class TestRulesCommandExecute:
    """Tests for RulesCommand.execute() method."""

    def test_execute_prints_prompt(self, capsys):
        """execute() prints the default system prompt."""
        args = Namespace()
        cmd = RulesCommand(args)
        exit_code = cmd.execute()

        captured = capsys.readouterr()
        assert exit_code == 0
        # Check that the prompt is printed to stdout
        assert "# Rule: File Output Format" in captured.out
        assert "project file" in captured.out

    def test_execute_prints_full_prompt(self, capsys):
        """execute() prints the complete default system prompt."""
        args = Namespace()
        cmd = RulesCommand(args)
        exit_code = cmd.execute()

        captured = capsys.readouterr()
        # Check key sections are present
        assert "Requirements" in captured.out
        assert "Markers" in captured.out
        assert "Compliance checklist" in captured.out

    def test_execute_copies_to_clipboard(self):
        """execute() copies the prompt to clipboard."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard") as mock_copy:
            exit_code = cmd.execute()

            assert exit_code == 0
            mock_copy.assert_called_once_with(DEFAULT_SYSTEM_PROMPT)

    def test_execute_shows_success_message(self, capsys):
        """execute() shows success message about clipboard."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard"):
            exit_code = cmd.execute()

            captured = capsys.readouterr()
            assert "✅" in captured.err
            assert "copied to clipboard" in captured.err

    def test_execute_returns_zero(self):
        """execute() returns exit code 0 on success."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard"):
            exit_code = cmd.execute()
            assert exit_code == 0

    def test_execute_still_prints_on_clipboard_error(self, capsys):
        """execute() still prints prompt even if clipboard copy fails."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard", side_effect=SystemExit(1)):
            try:
                cmd.execute()
            except SystemExit:
                pass

            captured = capsys.readouterr()
            # Prompt should have been printed before the error
            assert "# Rule: File Output Format" in captured.out


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

    def test_clipboard_copy_called_with_correct_content(self):
        """copy_to_clipboard is called with DEFAULT_SYSTEM_PROMPT."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard") as mock_copy:
            cmd.execute()
            # Verify the exact content is passed
            assert mock_copy.call_args[0][0] == DEFAULT_SYSTEM_PROMPT

    def test_clipboard_copy_error_propagates(self):
        """SystemExit from copy_to_clipboard is re-raised."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard", side_effect=SystemExit(1)):
            with pytest.raises(SystemExit):
                cmd.execute()

    def test_execute_order_print_before_copy(self, capsys):
        """execute() prints to stdout before attempting clipboard copy."""
        args = Namespace()
        cmd = RulesCommand(args)

        copy_called = []

        def track_copy(text):
            copy_called.append(True)
            captured = capsys.readouterr()
            # Verify stdout already has content before copy is called
            assert "# Rule:" in captured.out

        with patch("mdfs.commands.rules.copy_to_clipboard", side_effect=track_copy):
            cmd.execute()
            assert copy_called


class TestRulesCommandIntegration:
    """Integration tests for RulesCommand."""

    def test_rules_command_full_flow(self, capsys):
        """Full flow: print, copy, confirm."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard") as mock_copy:
            exit_code = cmd.execute()

            # Check exit code
            assert exit_code == 0

            # Check output
            captured = capsys.readouterr()
            assert "# Rule: File Output Format" in captured.out
            assert "✅" in captured.err
            assert "copied to clipboard" in captured.err

            # Check clipboard was called
            assert mock_copy.called

    def test_rules_command_multiple_executions(self, capsys):
        """RulesCommand can be executed multiple times."""
        args = Namespace()

        with patch("mdfs.commands.rules.copy_to_clipboard"):
            for _ in range(3):
                cmd = RulesCommand(args)
                exit_code = cmd.execute()
                assert exit_code == 0

            captured = capsys.readouterr()
            # Should see success message three times
            assert captured.err.count("✅") == 3

    def test_rules_command_with_different_args(self, capsys):
        """RulesCommand works with any Namespace args."""
        # Create a more complex Namespace
        args = Namespace(
            dir=".",
            command="rules",
            verbose=False,
            extra_field="extra_value"
        )

        with patch("mdfs.commands.rules.copy_to_clipboard"):
            cmd = RulesCommand(args)
            exit_code = cmd.execute()
            assert exit_code == 0

            captured = capsys.readouterr()
            assert "# Rule:" in captured.out


class TestRulesCommandErrorScenarios:
    """Tests for error scenarios in RulesCommand."""

    def test_execute_handles_clipboard_unavailable(self, capsys):
        """execute() handles unavailable clipboard gracefully."""
        args = Namespace()
        cmd = RulesCommand(args)

        # Simulate clipboard not available (common in headless environments)
        with patch("mdfs.commands.rules.copy_to_clipboard",
                   side_effect=SystemExit(1)):
            with pytest.raises(SystemExit):
                cmd.execute()

            # But the prompt should still have been printed
            captured = capsys.readouterr()
            assert "# Rule:" in captured.out

    def test_execute_handles_unexpected_error(self, capsys):
        """execute() handles unexpected errors in copy_to_clipboard."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard",
                   side_effect=RuntimeError("unexpected error")):
            with pytest.raises(RuntimeError):
                cmd.execute()

            captured = capsys.readouterr()
            # Prompt should still be printed
            assert "# Rule:" in captured.out

    def test_execute_with_empty_prompt(self):
        """execute() still works even if prompt is somehow empty."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.DEFAULT_SYSTEM_PROMPT", ""):
            with patch("mdfs.commands.rules.copy_to_clipboard") as mock_copy:
                exit_code = cmd.execute()
                assert exit_code == 0
                mock_copy.assert_called_once_with("")


class TestRulesCommandOutput:
    """Tests for output formatting in RulesCommand."""

    def test_output_to_stdout(self, capsys):
        """Prompt is printed to stdout."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard"):
            cmd.execute()

            captured = capsys.readouterr()
            # Prompt should be on stdout, not stderr
            assert "# Rule:" in captured.out
            assert "# Rule:" not in captured.err

    def test_success_message_to_stderr(self, capsys):
        """Success message is printed to stderr."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard"):
            cmd.execute()

            captured = capsys.readouterr()
            # Success message should be on stderr
            assert "✅" in captured.err
            assert "✅" not in captured.out

    def test_output_not_mixed(self, capsys):
        """stdout and stderr outputs are properly separated."""
        args = Namespace()
        cmd = RulesCommand(args)

        with patch("mdfs.commands.rules.copy_to_clipboard"):
            cmd.execute()

            captured = capsys.readouterr()
            # Prompt is in stdout
            assert len(captured.out) > 100
            # Message is in stderr
            assert "copied to clipboard" in captured.err


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
