"""
Shell setup utilities for managing shell completions and PATH configuration.

This module provides functions to:
- Detect the current shell (zsh, bash, fish)
- Manage marked configuration blocks in shell config files
- Handle symbolic links and backups
- Install and uninstall shell completions
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def detect_shell() -> str:
    """Detect the current shell.
    
    Returns:
        One of: "zsh", "bash", "fish", "unknown"
    
    Uses environment variables set by the shell itself:
    - ZSH_VERSION is set only by zsh
    - BASH_VERSION is set only by bash
    - FISH_VERSION is set only by fish (but may not be exported)
    
    Checks $SHELL environment variable as a fallback.
    """
    # Check environment variables set by the shell itself
    if os.environ.get("ZSH_VERSION"):
        return "zsh"
    if os.environ.get("BASH_VERSION"):
        return "bash"
    if os.environ.get("FISH_VERSION"):
        return "fish"
    
    # Fallback: check $SHELL environment variable
    shell_path = os.environ.get("SHELL", "").lower()
    if "zsh" in shell_path:
        return "zsh"
    if "bash" in shell_path:
        return "bash"
    if "fish" in shell_path:
        return "fish"
    
    return "unknown"


def get_shell_config_files(shell_type: str) -> dict[str, list[Path]]:
    """Get the configuration file paths for a given shell.
    
    Args:
        shell_type: One of "zsh", "bash", "fish"
    
    Returns:
        Dictionary with keys:
        - "env_files": Files that must exist in all contexts (PATH setup)
        - "rc_files": Files for interactive shells only (completions)
    """
    home = Path.home()
    
    if shell_type == "zsh":
        # Respect ZDOTDIR environment variable
        zdotdir = os.environ.get("ZDOTDIR")
        if zdotdir:
            zshenv = Path(zdotdir) / ".zshenv"
            zshrc = Path(zdotdir) / ".zshrc"
        else:
            zshenv = home / ".zshenv"
            zshrc = home / ".zshrc"
        
        return {
            "env_files": [zshenv],
            "rc_files": [zshrc],
        }
    
    elif shell_type == "bash":
        # On macOS, new terminal is a login shell; on Linux, it's usually non-login
        # Find existing profile file in priority order
        profile_file = None
        for candidate in [home / ".bash_profile", home / ".bash_login", home / ".profile"]:
            if candidate.exists():
                profile_file = candidate
                break
        
        # If none exists, use .bash_profile (macOS convention)
        if not profile_file:
            profile_file = home / ".bash_profile"
        
        bashrc = home / ".bashrc"
        
        return {
            "env_files": [profile_file],
            "rc_files": [bashrc],
        }
    
    elif shell_type == "fish":
        fish_config_dir = Path(os.environ.get("XDG_CONFIG_HOME", home / ".config")) / "fish"
        return {
            "env_files": [fish_config_dir / "conf.d" / "mdfs.fish"],
            "rc_files": [],  # fish auto-loads conf.d files
        }
    
    return {"env_files": [], "rc_files": []}


def resolve_symlink(path: Path) -> Path:
    """Resolve a symlink to its target.
    
    If the path is a symlink, returns the target.
    If the path is a regular file, returns the path as-is.
    
    Args:
        path: The file path to resolve
    
    Returns:
        The resolved (actual) file path
    """
    if path.is_symlink():
        return path.resolve()
    return path


def backup_file(file_path: Path) -> Optional[Path]:
    """Create a timestamped backup of a file.
    
    Only creates a backup if the file exists and doesn't already have a backup.
    
    Args:
        file_path: The file to backup
    
    Returns:
        Path to the backup file, or None if no backup was created
    """
    if not file_path.exists():
        return None
    
    # Check if we already have a backup for this session
    import time
    timestamp = int(time.time())
    backup_path = file_path.parent / f"{file_path.name}.mdfs-backup.{timestamp}"
    
    if not backup_path.exists():
        shutil.copy2(file_path, backup_path)
        return backup_path
    
    return None


def upsert_block(
    file_path: Path,
    block_content: str,
    marker_start: str,
    marker_end: str,
) -> None:
    """Add or update a marked block in a file (idempotent).
    
    If the block already exists, it is replaced. If it doesn't exist, it is appended.
    This ensures idempotency: running this function twice produces the same result.
    
    Handles:
    - File doesn't exist: creates it with the block
    - File exists, block absent: appends the block
    - File exists, block present: replaces the existing block
    - Symbolic links: resolves to the actual file before modifying
    
    Args:
        file_path: Path to the config file
        block_content: The content to insert (should include markers)
        marker_start: The opening marker line (e.g., "# >>> mdfs >>>")
        marker_end: The closing marker line (e.g., "# <<< mdfs <<<")
    
    Raises:
        PermissionError: If the file cannot be written
    """
    # Resolve symlinks to avoid breaking them with sed
    file_path = resolve_symlink(file_path)
    
    # Create file if it doesn't exist
    if not file_path.exists():
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(block_content + "\n", encoding="utf-8")
        return
    
    # Check write permissions
    if not os.access(file_path, os.W_OK):
        raise PermissionError(f"Cannot write to {file_path}")
    
    # Create backup before modification
    backup_file(file_path)
    
    # Read current content
    content = file_path.read_text(encoding="utf-8")
    
    # Check for corrupt state (opening marker without closing marker)
    has_start = marker_start in content
    has_end = marker_end in content
    if has_start and not has_end:
        # Log warning but continue
        pass  # Could log here if needed
    
    # Remove existing block if present
    if has_start:
        # Use regex to remove the block
        pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
        content = re.sub(pattern, "", content, flags=re.DOTALL)
        # Clean up extra newlines
        content = re.sub(r"\n\n\n+", "\n\n", content)
    
    # Append block with proper spacing
    content = content.rstrip()
    if content:
        content += "\n\n"
    content += block_content + "\n"
    
    file_path.write_text(content, encoding="utf-8")


def remove_block(
    file_path: Path,
    marker_start: str,
    marker_end: str,
) -> bool:
    """Remove a marked block from a file.
    
    Args:
        file_path: Path to the config file
        marker_start: The opening marker line
        marker_end: The closing marker line
    
    Returns:
        True if a block was removed, False otherwise
    """
    if not file_path.exists():
        return False
    
    # Resolve symlinks
    file_path = resolve_symlink(file_path)
    
    if not os.access(file_path, os.W_OK):
        raise PermissionError(f"Cannot write to {file_path}")
    
    content = file_path.read_text(encoding="utf-8")
    
    if marker_start not in content:
        return False
    
    # Create backup before modification
    backup_file(file_path)
    
    # Remove the block
    pattern = re.escape(marker_start) + r".*?" + re.escape(marker_end)
    new_content = re.sub(pattern, "", content, flags=re.DOTALL)
    
    # Clean up extra newlines
    new_content = re.sub(r"\n\n\n+", "\n\n", new_content)
    new_content = new_content.rstrip() + "\n"
    
    file_path.write_text(new_content, encoding="utf-8")
    return True


def get_completions_dir() -> Path:
    """Get the directory where shell completions are stored.
    
    Returns:
        Path to the completions directory (mdfs/completions)
    """
    return Path(__file__).parent / "completions"


def check_shell_completions(shell_type: str) -> bool:
    """Check if completions exist for the given shell.
    
    Args:
        shell_type: One of "zsh", "bash", "fish"
    
    Returns:
        True if completions exist, False otherwise
    """
    completions_dir = get_completions_dir()
    
    if shell_type == "zsh":
        return (completions_dir / "zsh" / "_mdfs").exists()
    elif shell_type == "bash":
        return (completions_dir / "bash" / "mdfs").exists()
    elif shell_type == "fish":
        return (completions_dir / "fish" / "mdfs.fish").exists()
    
    return False
