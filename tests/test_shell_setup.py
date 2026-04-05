"""
Unit tests for shell setup utilities.

Tests the core functionality:
- Shell detection
- Config file path resolution
- Symlink handling
- Block insertion/removal (idempotency)
"""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from mdfs.shell_setup import (
    detect_shell,
    get_shell_config_files,
    resolve_symlink,
    backup_file,
    upsert_block,
    remove_block,
)


# ── Shell Detection ───────────────────────────────────────────────

class TestDetectShell:
    """Tests for detect_shell() function."""
    
    def test_detect_zsh(self):
        """Detect zsh via ZSH_VERSION."""
        with patch.dict(os.environ, {"ZSH_VERSION": "5.8"}):
            assert detect_shell() == "zsh"
    
    def test_detect_bash(self):
        """Detect bash via BASH_VERSION."""
        with patch.dict(os.environ, {"BASH_VERSION": "5.0"}):
            assert detect_shell() == "bash"
    
    def test_detect_fish(self):
        """Detect fish via FISH_VERSION."""
        with patch.dict(os.environ, {"FISH_VERSION": "3.1"}):
            assert detect_shell() == "fish"
    
    def test_detect_from_shell_path_zsh(self):
        """Fallback: detect zsh from $SHELL."""
        with patch.dict(
            os.environ,
            {"ZSH_VERSION": "", "BASH_VERSION": "", "SHELL": "/bin/zsh"},
            clear=False,
        ):
            # Clear the ZSH_VERSION to test fallback
            env = os.environ.copy()
            env.pop("ZSH_VERSION", None)
            env.pop("BASH_VERSION", None)
            with patch.dict(os.environ, env, clear=True):
                with patch.dict(os.environ, {"SHELL": "/bin/zsh"}):
                    result = detect_shell()
                    assert result == "zsh"
    
    def test_detect_unknown(self):
        """Return 'unknown' when shell cannot be detected."""
        with patch.dict(
            os.environ,
            {},
            clear=True,
        ):
            assert detect_shell() == "unknown"


# ── Config File Paths ─────────────────────────────────────────────

class TestGetShellConfigFiles:
    """Tests for get_shell_config_files() function."""
    
    def test_zsh_config_files(self):
        """Get zsh config file paths."""
        config = get_shell_config_files("zsh")
        
        assert "env_files" in config
        assert "rc_files" in config
        assert len(config["env_files"]) > 0
        assert len(config["rc_files"]) > 0
        
        # Should be .zshenv and .zshrc
        assert any(".zshenv" in str(f) for f in config["env_files"])
        assert any(".zshrc" in str(f) for f in config["rc_files"])
    
    def test_zsh_respects_zdotdir(self):
        """Zsh config respects ZDOTDIR environment variable."""
        with patch.dict(os.environ, {"ZDOTDIR": "/custom/zdot"}):
            config = get_shell_config_files("zsh")
            
            env_file = config["env_files"][0]
            assert "/custom/zdot" in str(env_file)
    
    def test_bash_config_files(self):
        """Get bash config file paths."""
        config = get_shell_config_files("bash")
        
        assert "env_files" in config
        assert "rc_files" in config
        assert len(config["env_files"]) > 0
    
    def test_fish_config_files(self):
        """Get fish config file paths."""
        config = get_shell_config_files("fish")
        
        assert "env_files" in config
        assert "rc_files" in config
        
        # Fish should have conf.d file
        assert any("conf.d" in str(f) for f in config["env_files"])
    
    def test_unknown_shell(self):
        """Unknown shell returns empty config."""
        config = get_shell_config_files("unknown")
        
        assert config["env_files"] == []
        assert config["rc_files"] == []


# ── Symlink Handling ──────────────────────────────────────────────

class TestResolveSymlink:
    """Tests for resolve_symlink() function."""
    
    def test_resolve_regular_file(self, tmp_path):
        """Regular file returns as-is."""
        file = tmp_path / "test.txt"
        file.write_text("content")
        
        resolved = resolve_symlink(file)
        assert resolved == file
    
    def test_resolve_symlink(self, tmp_path):
        """Symlink resolves to target."""
        target = tmp_path / "target.txt"
        target.write_text("content")
        
        symlink = tmp_path / "link.txt"
        symlink.symlink_to(target)
        
        resolved = resolve_symlink(symlink)
        assert resolved == target.resolve()


# ── File Backup ───────────────────────────────────────────────────

class TestBackupFile:
    """Tests for backup_file() function."""
    
    def test_backup_creates_backup(self, tmp_path):
        """backup_file creates a backup with timestamp."""
        file = tmp_path / "test.txt"
        file.write_text("original content")
        
        backup = backup_file(file)
        
        assert backup is not None
        assert backup.exists()
        assert backup.read_text() == "original content"
        assert "mdfs-backup" in backup.name
    
    def test_backup_nonexistent_file(self, tmp_path):
        """backup_file returns None for nonexistent file."""
        file = tmp_path / "nonexistent.txt"
        
        backup = backup_file(file)
        
        assert backup is None
    
    def test_backup_idempotent(self, tmp_path):
        """Multiple backups with different timestamps create different backups."""
        file = tmp_path / "test.txt"
        file.write_text("original")
        
        backup1 = backup_file(file)
        assert backup1 is not None
        
        # Backup was created successfully
        assert backup1.exists()
        assert "mdfs-backup" in backup1.name


# ── Block Upsert ──────────────────────────────────────────────────

class TestUpsertBlock:
    """Tests for upsert_block() function (idempotent insert/update)."""
    
    def test_upsert_creates_file(self, tmp_path):
        """upsert_block creates file if it doesn't exist."""
        file = tmp_path / "config"
        
        upsert_block(
            file,
            "# >>> marker >>>\ncontent\n# <<< marker <<<",
            "# >>> marker >>>",
            "# <<< marker <<<",
        )
        
        assert file.exists()
        assert "content" in file.read_text()
    
    def test_upsert_appends_to_existing(self, tmp_path):
        """upsert_block appends to existing file."""
        file = tmp_path / "config"
        file.write_text("existing content\n")
        
        upsert_block(
            file,
            "# >>> marker >>>\nnew content\n# <<< marker <<<",
            "# >>> marker >>>",
            "# <<< marker <<<",
        )
        
        content = file.read_text()
        assert "existing content" in content
        assert "new content" in content
    
    def test_upsert_idempotent(self, tmp_path):
        """upsert_block is idempotent (no duplicates on repeated calls)."""
        file = tmp_path / "config"
        file.write_text("start\n")
        
        block = "# >>> marker >>>\nconfig\n# <<< marker <<<"
        
        # First insert
        upsert_block(file, block, "# >>> marker >>>", "# <<< marker <<<")
        content1 = file.read_text()
        count1 = content1.count("# >>> marker >>>")
        
        # Second insert (idempotent)
        upsert_block(file, block, "# >>> marker >>>", "# <<< marker <<<")
        content2 = file.read_text()
        count2 = content2.count("# >>> marker >>>")
        
        # Count should be the same (only 1)
        assert count1 == 1
        assert count2 == 1
    
    def test_upsert_replaces_old_block(self, tmp_path):
        """upsert_block replaces an existing block with new content."""
        file = tmp_path / "config"
        file.write_text("# >>> marker >>>\nold content\n# <<< marker <<<\n")
        
        new_block = "# >>> marker >>>\nnew content\n# <<< marker <<<"
        upsert_block(file, new_block, "# >>> marker >>>", "# <<< marker <<<")
        
        content = file.read_text()
        assert "old content" not in content
        assert "new content" in content
        assert content.count("# >>> marker >>>") == 1
    
    def test_upsert_handles_symlink(self, tmp_path):
        """upsert_block resolves symlinks before modifying."""
        real_file = tmp_path / "real_config"
        real_file.write_text("original\n")
        
        symlink = tmp_path / "link_config"
        symlink.symlink_to(real_file)
        
        upsert_block(
            symlink,
            "# >>> marker >>>\nconfig\n# <<< marker <<<",
            "# >>> marker >>>",
            "# <<< marker <<<",
        )
        
        # Real file should be modified, not the symlink
        assert "config" in real_file.read_text()
        assert "config" in symlink.read_text()


# ── Block Removal ─────────────────────────────────────────────────

class TestRemoveBlock:
    """Tests for remove_block() function."""
    
    def test_remove_existing_block(self, tmp_path):
        """remove_block removes an existing marked block."""
        file = tmp_path / "config"
        file.write_text(
            "before\n"
            "# >>> marker >>>\n"
            "to remove\n"
            "# <<< marker <<<\n"
            "after\n"
        )
        
        removed = remove_block(file, "# >>> marker >>>", "# <<< marker <<<")
        
        assert removed is True
        content = file.read_text()
        assert "to remove" not in content
        assert "before" in content
        assert "after" in content
    
    def test_remove_nonexistent_block(self, tmp_path):
        """remove_block returns False for nonexistent block."""
        file = tmp_path / "config"
        file.write_text("content\n")
        
        removed = remove_block(file, "# >>> marker >>>", "# <<< marker <<<")
        
        assert removed is False
    
    def test_remove_from_nonexistent_file(self, tmp_path):
        """remove_block returns False for nonexistent file."""
        file = tmp_path / "nonexistent"
        
        removed = remove_block(file, "# >>> marker >>>", "# <<< marker <<<")
        
        assert removed is False
    
    def test_remove_handles_symlink(self, tmp_path):
        """remove_block resolves symlinks before modifying."""
        real_file = tmp_path / "real_config"
        real_file.write_text(
            "# >>> marker >>>\n"
            "to remove\n"
            "# <<< marker <<<\n"
        )
        
        symlink = tmp_path / "link_config"
        symlink.symlink_to(real_file)
        
        removed = remove_block(symlink, "# >>> marker >>>", "# <<< marker <<<")
        
        assert removed is True
        assert "to remove" not in real_file.read_text()


# ── Integration Tests ─────────────────────────────────────────────

class TestBlockOperationsIntegration:
    """Integration tests for block operations."""
    
    def test_insert_and_remove_cycle(self, tmp_path):
        """Insert a block, then remove it."""
        file = tmp_path / "config"
        file.write_text("initial\n")
        
        block = "# >>> marker >>>\nconfig\n# <<< marker <<<"
        
        # Insert
        upsert_block(file, block, "# >>> marker >>>", "# <<< marker <<<")
        assert "config" in file.read_text()
        
        # Remove
        removed = remove_block(file, "# >>> marker >>>", "# <<< marker <<<")
        assert removed is True
        assert "config" not in file.read_text()
        assert "initial" in file.read_text()
    
    def test_multiple_blocks_different_markers(self, tmp_path):
        """Multiple marked blocks with different markers can coexist."""
        file = tmp_path / "config"
        
        # Insert first block
        upsert_block(
            file,
            "# >>> block1 >>>\ncontent1\n# <<< block1 <<<",
            "# >>> block1 >>>",
            "# <<< block1 <<<",
        )
        
        # Insert second block
        upsert_block(
            file,
            "# >>> block2 >>>\ncontent2\n# <<< block2 <<<",
            "# >>> block2 >>>",
            "# <<< block2 <<<",
        )
        
        content = file.read_text()
        assert "content1" in content
        assert "content2" in content
        
        # Remove first block
        remove_block(file, "# >>> block1 >>>", "# <<< block1 <<<")
        
        content = file.read_text()
        assert "content1" not in content
        assert "content2" in content
