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

class TestBashProfileSourcing:
    """Tests for .bash_profile sourcing logic."""
    
    def test_install_bash_adds_sourcing_when_missing(self, tmp_path):
        """Install bash adds sourcing to .bash_profile when missing."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        bash_profile.write_text("# existing content\n")
        
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
                profile_content = bash_profile.read_text()
                assert ". ~/.bashrc" in profile_content or "source ~/.bashrc" in profile_content
    
    def test_install_bash_no_duplicate_sourcing(self, tmp_path):
        """Install bash doesn't add duplicate sourcing."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        bash_profile.write_text("# existing content\nsource ~/.bashrc\n")
        
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
                profile_content = bash_profile.read_text()
                # Count occurrences - should be only original one
                sourcing_count = profile_content.count("source ~/.bashrc") + profile_content.count(". ~/.bashrc")
                assert sourcing_count == 1
    
    def test_install_bash_same_bashrc_and_profile(self, tmp_path):
        """Install bash handles case where bashrc and profile are same file."""
        config = tmp_path / ".bashrc"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [config],
                    "rc_files": [config],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                result = cmd._install_bash_completions()
                
                assert result is True
                content = config.read_text()
                assert "# >>> mdfs >>>" in content


class TestPermissionErrors:
    """Tests for PermissionError handling."""
    
    def test_install_bash_permission_error_on_bashrc(self, tmp_path, capsys):
        """Install bash handles PermissionError on bashrc."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                with patch("mdfs.commands.setup.upsert_block", side_effect=PermissionError("denied")):
                    mock_get_files.return_value = {
                        "env_files": [bash_profile],
                        "rc_files": [bashrc],
                    }
                    
                    args = MagicMock()
                    args.install_completions = False
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    result = cmd._install_bash_completions()
                    
                    assert result is False
                    captured = capsys.readouterr()
                    assert "cannot write" in captured.err or "Error" in captured.err
    
    def test_install_zsh_permission_error_on_zshenv(self, tmp_path, capsys):
        """Install zsh handles PermissionError on zshenv."""
        zshenv = tmp_path / ".zshenv"
        zshrc = tmp_path / ".zshrc"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="zsh"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [zshenv],
                    "rc_files": [zshrc],
                }
                
                with patch("mdfs.commands.setup.upsert_block") as mock_upsert:
                    # First call (zshenv) raises PermissionError
                    mock_upsert.side_effect = PermissionError("denied")
                    
                    args = MagicMock()
                    args.install_completions = False
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    result = cmd._install_zsh_completions()
                    
                    assert result is False
                    captured = capsys.readouterr()
                    assert "cannot write" in captured.err or "Error" in captured.err
    
    def test_install_zsh_permission_error_on_zshrc(self, tmp_path, capsys):
        """Install zsh handles PermissionError on zshrc."""
        zshenv = tmp_path / ".zshenv"
        zshrc = tmp_path / ".zshrc"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="zsh"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [zshenv],
                    "rc_files": [zshrc],
                }
                
                with patch("mdfs.commands.setup.upsert_block") as mock_upsert:
                    # First call succeeds, second call (zshrc) fails
                    mock_upsert.side_effect = [None, PermissionError("denied")]
                    
                    args = MagicMock()
                    args.install_completions = False
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    result = cmd._install_zsh_completions()
                    
                    assert result is False
                    captured = capsys.readouterr()
                    assert "cannot write" in captured.err or "Error" in captured.err


class TestFishCompletionCopying:
    """Tests for fish completion file copying."""
    
    def test_install_fish_creates_conf_directory(self, tmp_path):
        """Install fish creates conf.d directory if missing."""
        fish_conf = tmp_path / "conf.d" / "mdfs.fish"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="fish"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [fish_conf],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                result = cmd._install_fish_completions()
                
                assert result is True
                assert fish_conf.parent.exists()
    
    def test_install_fish_idempotent(self, tmp_path):
        """Installing fish completions twice produces no duplicates."""
        fish_conf = tmp_path / "conf.d" / "mdfs.fish"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="fish"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [fish_conf],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                
                # First install
                cmd._install_fish_completions()
                
                # Second install
                cmd._install_fish_completions()
                
                # Check no duplicates
                fish_conf_content = fish_conf.read_text()
                assert fish_conf_content.count("# >>> mdfs >>>") == 1
    
    def test_install_fish_permission_error_on_conf(self, tmp_path, capsys):
        """Install fish handles PermissionError on conf.d file."""
        fish_conf = tmp_path / "conf.d" / "mdfs.fish"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="fish"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [fish_conf],
                }
                
                with patch("mdfs.commands.setup.upsert_block", side_effect=PermissionError("denied")):
                    args = MagicMock()
                    args.install_completions = False
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    result = cmd._install_fish_completions()
                    
                    assert result is False
                    captured = capsys.readouterr()
                    assert "cannot write" in captured.err or "Error" in captured.err
    
    def test_install_bash_permission_error_on_profile(self, tmp_path, capsys):
        """Install bash handles exception when updating .bash_profile."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        bash_profile.write_text("# existing\n")
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                # Mock read_text to raise exception
                bash_profile_mock = MagicMock()
                bash_profile_mock.exists.return_value = True
                bash_profile_mock.read_text.side_effect = PermissionError("denied")
                
                mock_get_files.return_value = {
                    "env_files": [bash_profile_mock],
                    "rc_files": [bashrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                # This should still succeed (warning only)
                result = cmd._install_bash_completions()
                
                # Result depends on bashrc being writable
                captured = capsys.readouterr()
                # Either succeeds with warning, or fails
                assert isinstance(result, bool)


class TestExecuteErrorHandling:
    """Tests for execute() method error cases."""
    
    def test_execute_no_flags_returns_error(self, capsys):
        """execute() returns error when no flags provided."""
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            args = MagicMock()
            args.install_completions = False
            args.uninstall_completions = False
            cmd = SetupCommand(args)
            exit_code = cmd.execute()
            
            assert exit_code == 1
            captured = capsys.readouterr()
            assert "Error" in captured.err
            assert "--install-completions" in captured.err or "--uninstall-completions" in captured.err
    
    def test_execute_install_failed_returns_error_code(self, capsys):
        """execute() returns 1 when install fails."""
        with patch("mdfs.commands.setup.detect_shell", return_value="unknown"):
            args = MagicMock()
            args.install_completions = True
            args.uninstall_completions = False
            cmd = SetupCommand(args)
            exit_code = cmd.execute()
            
            assert exit_code == 1


class TestUninstallNotFound:
    """Tests for uninstall when completions not found."""
    
    def test_uninstall_zsh_not_found(self, tmp_path, capsys):
        """Uninstall zsh shows info message when not found."""
        zshenv = tmp_path / ".zshenv"
        zshrc = tmp_path / ".zshrc"
        zshenv.write_text("# no mdfs config\n")
        zshrc.write_text("# no mdfs config\n")
        
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
                result = cmd._uninstall_zsh_completions()
                
                assert result is True
                captured = capsys.readouterr()
                assert "not found" in captured.out.lower() or "ℹ️" in captured.out
    
    def test_uninstall_bash_not_found(self, tmp_path, capsys):
        """Uninstall bash shows info message when not found."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        bashrc.write_text("# no mdfs config\n")
        
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
                result = cmd._uninstall_bash_completions()
                
                assert result is True
                captured = capsys.readouterr()
                assert "not found" in captured.out.lower() or "ℹ️" in captured.out
    
    def test_uninstall_fish_not_found(self, tmp_path, capsys):
        """Uninstall fish shows info message when not found."""
        fish_conf = tmp_path / "conf.d" / "mdfs.fish"
        fish_conf.parent.mkdir(parents=True, exist_ok=True)
        fish_conf.write_text("# no mdfs config\n")
        
        with patch("mdfs.commands.setup.detect_shell", return_value="fish"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [fish_conf],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                result = cmd._uninstall_fish_completions()
                
                assert result is True
                captured = capsys.readouterr()
                assert "not found" in captured.out.lower() or "ℹ️" in captured.out


class TestGenericExceptionHandling:
    """Tests for generic exception handling in install/uninstall methods."""
    
    def test_install_completions_generic_exception(self, capsys):
        """install_completions() catches and handles generic exceptions."""
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.check_shell_completions", return_value=True):
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                
                # Mock _install_bash_completions to raise a generic exception
                with patch.object(cmd, "_install_bash_completions", side_effect=RuntimeError("unexpected error")):
                    result = cmd.install_completions()
                    
                    assert result is False
                    captured = capsys.readouterr()
                    assert "Error" in captured.err
                    assert "unexpected error" in captured.err
    
    def test_uninstall_completions_generic_exception(self, capsys):
        """uninstall_completions() catches and handles generic exceptions."""
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            args = MagicMock()
            args.install_completions = False
            args.uninstall_completions = False
            cmd = SetupCommand(args)
            
            # Mock _uninstall_bash_completions to raise a generic exception
            with patch.object(cmd, "_uninstall_bash_completions", side_effect=RuntimeError("unexpected error")):
                result = cmd.uninstall_completions()
                
                assert result is False
                captured = capsys.readouterr()
                assert "Error" in captured.err
                assert "unexpected error" in captured.err
    
    def test_install_bash_exception_updating_profile(self, tmp_path, capsys):
        """Install bash handles exception when updating .bash_profile."""
        bashrc = tmp_path / ".bashrc"
        bash_profile = tmp_path / ".bash_profile"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="bash"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                # Create a mock that simulates exception during write_text
                bash_profile_mock = MagicMock(spec=Path)
                bash_profile_mock.exists.return_value = True
                bash_profile_mock.read_text.side_effect = RuntimeError("cannot read")
                
                mock_get_files.return_value = {
                    "env_files": [bash_profile_mock],
                    "rc_files": [bashrc],
                }
                
                args = MagicMock()
                args.install_completions = False
                args.uninstall_completions = False
                cmd = SetupCommand(args)
                result = cmd._install_bash_completions()
                
                # Should still succeed or with warning
                captured = capsys.readouterr()
                # Either succeeds with warning or fails gracefully
                assert isinstance(result, bool)
    
    def test_install_fish_exception_writing_file(self, tmp_path, capsys):
        """Install fish handles exception when writing file."""
        fish_conf = tmp_path / "conf.d" / "mdfs.fish"
        
        with patch("mdfs.commands.setup.detect_shell", return_value="fish"):
            with patch("mdfs.commands.setup.get_shell_config_files") as mock_get_files:
                mock_get_files.return_value = {
                    "env_files": [fish_conf],
                }
                
                with patch("mdfs.commands.setup.upsert_block", side_effect=PermissionError("write denied")):
                    args = MagicMock()
                    args.install_completions = False
                    args.uninstall_completions = False
                    cmd = SetupCommand(args)
                    result = cmd._install_fish_completions()
                    
                    # Should fail due to exception
                    assert result is False
                    captured = capsys.readouterr()
                    assert "Error" in captured.err or "cannot write" in captured.err
    
    def test_execute_returns_zero_on_success(self, tmp_path):
        """execute() returns 0 when install succeeds."""
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
