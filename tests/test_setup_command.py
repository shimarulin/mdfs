"""
Integration tests for the setup command.

Tests the SetupCommand class:
- Installation of completions (zsh, bash, fish)
- Uninstallation of completions
- Idempotency
- Error handling
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from io import StringIO

import pytest

from mdfs.commands.setup import SetupCommand
from mdfs.shell_setup import remove_block


# ── Setup Command Tests ───────────────────────────────────────────

class TestSetupCommandInitialization:
    """Tests for SetupCommand initialization."""
    
    def test_init_detects_shell(self):
        """SetupCommand detects the current shell on initialization."""
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            args = MagicMock()
            args.install_completions = False
            args.uninstall_completions = False
            cmd = SetupCommand(args)
            assert cmd.shell_type == "bash"
    
    def test_init_gets_completions_dir(self):
        """SetupCommand gets completions directory path."""
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            args = MagicMock()
            args.install_completions = False
            args.uninstall_completions = False
            cmd = SetupCommand(args)
            assert cmd.completions_dir.name == "completions"
            # The directory may not exist yet, but the path is correct
            assert "completions" in str(cmd.completions_dir)


# ── Installation Tests ────────────────────────────────────────────

class TestInstallZshCompletions:
    """Tests for zsh completions installation."""
    
    def test_install_zsh_succeeds_when_completions_exist(self):
        """Installing zsh completions succeeds when they exist."""
        with patch("mdfs.commands.setup.detect_shell", return_value="zsh"):
            with patch("mdfs.commands.setup.check_shell_completions", return_value=True):
                with patch.object(SetupCommand, "_install_zsh_completions", return_value=True):
                    args = MagicMock()
                    args.install_completions = False
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    success = cmd.install_completions()
                    assert success is True
    
    def test_install_zsh_method_updates_files(self, tmp_path):
        """_install_zsh_completions updates config files correctly."""
        zshenv = tmp_path / ".zshenv"
        zshrc = tmp_path / ".zshrc"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="zsh"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [zshenv],
                    "rc_files": [zshrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                result = cmd._install_zsh_completions()
                
                assert result is True
                assert zshenv.exists()
                assert zshrc.exists()
                assert "fpath=" in zshenv.read_text()
                assert "compinit" in zshrc.read_text()
    
    def test_install_zsh_idempotent(self, tmp_path):
        """Installing zsh completions twice produces no duplicates."""
        zshenv = tmp_path / ".zshenv"
        zshrc = tmp_path / ".zshrc"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="zsh"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [zshenv],
                    "rc_files": [zshrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                
                # First install
                cmd._install_zsh_completions()
                
                # Second install
                cmd._install_zsh_completions()
                
                # Check no duplicates
                zshenv_content = zshenv.read_text()
                zshrc_content = zshrc.read_text()
                
                assert zshenv_content.count("# >>> mdfs >>>") == 1
                assert zshrc_content.count("# >>> mdfs >>>") == 1


class TestInstallBashCompletions:
    """Tests for bash completions installation."""
    
    def test_install_bash_succeeds_when_completions_exist(self):
        """Installing bash completions succeeds when they exist."""
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.check_shell_completions", return_value=True):
                with patch.object(SetupCommand, "_install_bash_completions", return_value=True):
                    args = MagicMock()
                    args.install_completions = False
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    success = cmd.install_completions()
                    assert success is True
    
    def test_install_bash_method_updates_files(self, tmp_path):
        """_install_bash_completions updates config files correctly."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [bash_profile],
                    "rc_files": [bashrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                result = cmd._install_bash_completions()
                
                assert result is True
                assert bashrc.exists()
                assert "# >>> mdfs >>>" in bashrc.read_text()
    
    def test_install_bash_idempotent(self, tmp_path):
        """Installing bash completions twice produces no duplicates."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [bash_profile],
                    "rc_files": [bashrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                
                # First install
                cmd._install_bash_completions()
                
                # Second install
                cmd._install_bash_completions()
                
                # Check no duplicates
                bashrc_content = bashrc.read_text()
                assert bashrc_content.count("# >>> mdfs >>>") == 1


class TestInstallFishCompletions:
    """Tests for fish completions installation."""
    
    def test_install_fish_succeeds_when_completions_exist(self):
        """Installing fish completions succeeds when they exist."""
        with patch("mdfs.commands.setup.detect_shell", return_value="fish"):
            with patch("mdfs.commands.setup.check_shell_completions", return_value=True):
                with patch.object(SetupCommand, "_install_fish_completions", return_value=True):
                    args = MagicMock()
                    args.install_completions = False
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    success = cmd.install_completions()
                    assert success is True


# ── Uninstallation Tests ──────────────────────────────────────────

class TestUninstallZshCompletions:
    """Tests for zsh completions uninstallation."""
    
    def test_uninstall_zsh_removes_config(self, tmp_path):
        """Uninstalling zsh completions removes configuration."""
        zshenv = tmp_path / ".zshenv"
        zshrc = tmp_path / ".zshrc"
        
        # Setup config
        zshenv.write_text("# >>> mdfs >>>\nconfig\n# <<< mdfs <<<\noriginal\n")
        zshrc.write_text("# >>> mdfs >>>\nconfig\n# <<< mdfs <<<\noriginal\n")
        
        with patch("mdfs.commands.setup.detect_shell", return_value="zsh"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [zshenv],
                    "rc_files": [zshrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                cmd._uninstall_zsh_completions()
        
        # Check removed
        zshenv_content = zshenv.read_text()
        zshrc_content = zshrc.read_text()
        
        assert "# >>> mdfs >>>" not in zshenv_content
        assert "# >>> mdfs >>>" not in zshrc_content
        assert "original" in zshenv_content
        assert "original" in zshrc_content


class TestUninstallBashCompletions:
    """Tests for bash completions uninstallation."""
    
    def test_uninstall_bash_removes_config(self, tmp_path):
        """Uninstalling bash completions removes configuration."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        
        # Setup config
        bashrc.write_text("# >>> mdfs >>>\nconfig\n# <<< mdfs <<<\noriginal\n")
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [bash_profile],
                    "rc_files": [bashrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                cmd._uninstall_bash_completions()
        
        # Check removed
        bashrc_content = bashrc.read_text()
        assert "# >>> mdfs >>>" not in bashrc_content
        assert "original" in bashrc_content


# ── Error Handling Tests ──────────────────────────────────────────

class TestErrorHandling:
    """Tests for error handling in SetupCommand."""
    
    def test_install_unknown_shell_fails(self, capsys):
        """Installation fails gracefully for unknown shell."""
        with patch("mdfs.commands.setup.detect_shell", return_value="unknown"):
            args = MagicMock()
            args.install_completions = False
            args.uninstall_completions = False
            cmd = SetupCommand(args)
            success = cmd.install_completions()
            
            assert success is False
            captured = capsys.readouterr()
            assert "Error" in captured.err
    
    def test_uninstall_unknown_shell_fails(self, capsys):
        """Uninstallation fails gracefully for unknown shell."""
        with patch("mdfs.commands.setup.detect_shell", return_value="unknown"):
            args = MagicMock()
            args.install_completions = False
            args.uninstall_completions = False
            cmd = SetupCommand(args)
            success = cmd.uninstall_completions()
            
            assert success is False
            captured = capsys.readouterr()
            assert "Error" in captured.err
    
    def test_install_missing_completions_fails(self, capsys):
        """Installation fails if completions don't exist."""
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.check_shell_completions", return_value=False):
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                success = cmd.install_completions()
                
                assert success is False
                captured = capsys.readouterr()
                assert "Error" in captured.err


# ── Execute Method Tests ──────────────────────────────────────────

class TestExecuteMethod:
    """Tests for SetupCommand.execute() method."""
    
    def test_execute_install(self, tmp_path):
        """execute() with install_completions=True calls install_completions."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                with patch("mdfs.commands.setup.check_shell_completions", return_value=True):
                    mock_get_files.return_value = {
                        "env_files": [bash_profile],
                        "rc_files": [bashrc],
                    }
                    
                    args = MagicMock()
                    args.install_completions = True
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    exit_code = cmd.execute()
                    
                    assert exit_code == 0
                    assert bashrc.exists()
    
    def test_execute_uninstall(self, tmp_path):
        """execute() with uninstall_completions=True calls uninstall_completions."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        
        # Setup config
        bashrc.write_text("# >>> mdfs >>>\nconfig\n# <<< mdfs <<<\noriginal\n")
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [bash_profile],
                    "rc_files": [bashrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = True
                cmd = SetupCommand(args)
                exit_code = cmd.execute()
                
                assert exit_code == 0
                # Block should be removed
                content = bashrc.read_text()
                assert "# >>> mdfs >>>" not in content
                assert "original" in content
    
    def test_execute_install_returns_error_code_on_failure(self, capsys):
        """execute() returns 1 on failure."""
        with patch("mdfs.commands.setup.detect_shell", return_value="unknown"):
            args = MagicMock()
            args.install_completions = True
            args.uninstall_completions = False
            cmd = SetupCommand(args)
            exit_code = cmd.execute()
            
            assert exit_code == 1


# ── Integration End-to-End Tests ──────────────────────────────────

class TestEndToEnd:
    """End-to-end tests for setup command."""
    
    def test_install_then_uninstall_bash(self, tmp_path):
        """Install and then uninstall bash completions."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                with patch("mdfs.commands.setup.check_shell_completions", return_value=True):
                    mock_get_files.return_value = {
                        "env_files": [bash_profile],
                        "rc_files": [bashrc],
                    }
                    
                    args = MagicMock()
                    args.install_completions = True
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    
                    # Install
                    assert cmd.execute() == 0
                    assert bashrc.exists()
                    content_after_install = bashrc.read_text()
                    assert "# >>> mdfs >>>" in content_after_install
                    
                    # Uninstall
                    args.install_completions = False
                    args.uninstall_completions = True
                    assert cmd.execute() == 0
                    content_after_uninstall = bashrc.read_text()
                    assert "# >>> mdfs >>>" not in content_after_uninstall
    
    def test_install_then_uninstall_zsh(self, tmp_path):
        """Install and then uninstall zsh completions."""
        zshenv = tmp_path / ".zshenv"
        zshrc = tmp_path / ".zshrc"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="zsh"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                with patch("mdfs.commands.setup.check_shell_completions", return_value=True):
                    mock_get_files.return_value = {
                        "env_files": [zshenv],
                        "rc_files": [zshrc],
                    }
                    
                    args = MagicMock()
                    args.install_completions = True
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    
                    # Install
                    assert cmd.execute() == 0
                    assert zshenv.exists()
                    assert zshrc.exists()
                    
                    zshenv_content = zshenv.read_text()
                    zshrc_content = zshrc.read_text()
                    assert "# >>> mdfs >>>" in zshenv_content
                    assert "# >>> mdfs >>>" in zshrc_content
                    
                    # Uninstall
                    args.install_completions = False
                    args.uninstall_completions = True
                    assert cmd.execute() == 0
                    zshenv_content = zshenv.read_text()
                    zshrc_content = zshrc.read_text()
                    assert "# >>> mdfs >>>" not in zshenv_content
                    assert "# >>> mdfs >>>" not in zshrc_content
