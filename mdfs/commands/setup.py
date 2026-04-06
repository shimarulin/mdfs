"""
Setup command for installing and uninstalling shell completions.

This module provides the `mdfs setup` command which handles:
- Installing shell completions (zsh, bash, fish)
- Uninstalling shell completions
- Providing helpful messages about next steps
"""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from ..shell_setup import (
    detect_shell,
    get_shell_config_files,
    upsert_block,
    remove_block,
    check_shell_completions,
    get_completions_dir,
)
from .base import BaseCommand


class SetupCommand(BaseCommand):
    """Command for managing shell setup and completions."""
    
    MARKER_START = "# >>> mdfs >>>"
    MARKER_END = "# <<< mdfs <<<"
    
    def __init__(self, args: Namespace):
        """Initialize the setup command.
        
        Args:
            args: Parsed command-line arguments
        """
        self.args = args
        self.shell_type = detect_shell()
        self.completions_dir = get_completions_dir()
        # Setup command doesn't require .mdfs directory
        self.root = Path.cwd()
    
    def install_completions(self) -> bool:
        """Install shell completions for the current shell.
        
        Returns:
            True if installation succeeded, False otherwise
        """
        if self.shell_type == "unknown":
            print(
                "Error: could not detect your shell.",
                file=sys.stderr,
            )
            print(
                "Supported shells: zsh, bash, fish",
                file=sys.stderr,
            )
            return False
        
        if not check_shell_completions(self.shell_type):
            print(
                f"Error: shell completions not found for {self.shell_type}.",
                file=sys.stderr,
            )
            return False
        
        try:
            if self.shell_type == "zsh":
                return self._install_zsh_completions()
            elif self.shell_type == "bash":
                return self._install_bash_completions()
            elif self.shell_type == "fish":
                return self._install_fish_completions()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return False
        
        return False
    
    def uninstall_completions(self) -> bool:
        """Uninstall shell completions for the current shell.
        
        Returns:
            True if uninstallation succeeded, False otherwise
        """
        if self.shell_type == "unknown":
            print(
                "Error: could not detect your shell.",
                file=sys.stderr,
            )
            return False
        
        try:
            if self.shell_type == "zsh":
                return self._uninstall_zsh_completions()
            elif self.shell_type == "bash":
                return self._uninstall_bash_completions()
            elif self.shell_type == "fish":
                return self._uninstall_fish_completions()
        except Exception as e:
            print(f"Error: {e}", file=sys.stderr)
            return False
        
        return False
    
    def _install_zsh_completions(self) -> bool:
        """Install completions for zsh.
        
        Adds fpath and completion initialization to zsh config files.
        """
        config_files = get_shell_config_files("zsh")
        zshenv = config_files["env_files"][0]
        zshrc = config_files["rc_files"][0]
        
        completions_dir = self.completions_dir / "zsh"
        
        # Build the block for .zshenv (fpath setup)
        env_block = f"""{self.MARKER_START}
fpath=({completions_dir} $fpath)
{self.MARKER_END}"""
        
        try:
            upsert_block(zshenv, env_block, self.MARKER_START, self.MARKER_END)
            print(f"✅ Updated {zshenv}")
        except PermissionError:
            print(f"Error: cannot write to {zshenv}", file=sys.stderr)
            return False
        
        # Build the block for .zshrc (compinit)
        rc_block = f"""{self.MARKER_START}
autoload -Uz compinit && compinit -i
{self.MARKER_END}"""
        
        try:
            upsert_block(zshrc, rc_block, self.MARKER_START, self.MARKER_END)
            print(f"✅ Updated {zshrc}")
        except PermissionError:
            print(f"Error: cannot write to {zshrc}", file=sys.stderr)
            return False
        
        print("")
        print("✅ Shell completions installed for zsh")
        print("")
        print("Next step: open a new terminal window")
        print(f"(or run: source {zshenv})")
        
        return True
    
    def _install_bash_completions(self) -> bool:
        """Install completions for bash.
        
        Adds completion sourcing to bash config files.
        """
        config_files = get_shell_config_files("bash")
        profile_file = config_files["env_files"][0]
        bashrc = config_files["rc_files"][0]
        
        completions_file = self.completions_dir / "bash" / "mdfs"
        
        # Build the block
        block = f"""{self.MARKER_START}
[ -f {completions_file} ] && . {completions_file}
{self.MARKER_END}"""
        
        try:
            upsert_block(bashrc, block, self.MARKER_START, self.MARKER_END)
            print(f"✅ Updated {bashrc}")
        except PermissionError:
            print(f"Error: cannot write to {bashrc}", file=sys.stderr)
            return False
        
        # Ensure .bash_profile sources .bashrc on macOS
        if profile_file != bashrc and profile_file.exists():
            try:
                content = profile_file.read_text(encoding="utf-8")
                if not any(
                    pattern in content
                    for pattern in [". ~/.bashrc", "source ~/.bashrc", ". $HOME/.bashrc", "source $HOME/.bashrc"]
                ):
                    # Add sourcing of .bashrc
                    if not content.endswith("\n"):
                        content += "\n"
                    content += f"\n# Source .bashrc\n[ -f ~/.bashrc ] && . ~/.bashrc\n"
                    profile_file.write_text(content, encoding="utf-8")
                    print(f"✅ Updated {profile_file} to source .bashrc")
            except Exception as e:
                print(f"Warning: could not update {profile_file}: {e}", file=sys.stderr)
        
        print("")
        print("✅ Shell completions installed for bash")
        print("")
        print("Next step: open a new terminal window")
        print(f"(or run: source {bashrc})")
        
        return True
    
    def _install_fish_completions(self) -> bool:
        """Install completions for fish.
        
        Copies completion file to fish config directory.
        """
        config_files = get_shell_config_files("fish")
        fish_conf_file = config_files["env_files"][0]
        
        # Create conf.d directory
        fish_conf_file.parent.mkdir(parents=True, exist_ok=True)
        
        completions_src = self.completions_dir / "fish" / "mdfs.fish"
        
        # Build the block
        block = f"""{self.MARKER_START}
fish_add_path {self.completions_dir.parent / 'bin'}
{self.MARKER_END}"""
        
        try:
            upsert_block(fish_conf_file, block, self.MARKER_START, self.MARKER_END)
            print(f"✅ Updated {fish_conf_file}")
        except PermissionError:
            print(f"Error: cannot write to {fish_conf_file}", file=sys.stderr)
            return False
        
        # Copy completion file
        try:
            fish_completions_dir = fish_conf_file.parent.parent / "completions"
            fish_completions_dir.mkdir(parents=True, exist_ok=True)
            
            fish_completions_file = fish_completions_dir / "mdfs.fish"
            if completions_src.exists():
                import shutil
                shutil.copy2(completions_src, fish_completions_file)
                print(f"✅ Copied {fish_completions_file}")
        except Exception as e:
            print(f"Warning: could not copy completion file: {e}", file=sys.stderr)
        
        print("")
        print("✅ Shell completions installed for fish")
        print("")
        print("Next step: open a new fish shell")
        
        return True
    
    def _uninstall_zsh_completions(self) -> bool:
        """Uninstall completions from zsh config files."""
        config_files = get_shell_config_files("zsh")
        zshenv = config_files["env_files"][0]
        zshrc = config_files["rc_files"][0]
        
        removed_count = 0
        
        if remove_block(zshenv, self.MARKER_START, self.MARKER_END):
            print(f"✅ Removed from {zshenv}")
            removed_count += 1
        
        if remove_block(zshrc, self.MARKER_START, self.MARKER_END):
            print(f"✅ Removed from {zshrc}")
            removed_count += 1
        
        if removed_count == 0:
            print("ℹ️  mdfs completions not found in zsh config")
        else:
            print("")
            print("✅ Shell completions uninstalled for zsh")
            print("")
            print("Next step: open a new terminal window")
        
        return True
    
    def _uninstall_bash_completions(self) -> bool:
        """Uninstall completions from bash config files."""
        config_files = get_shell_config_files("bash")
        bashrc = config_files["rc_files"][0]
        
        removed = remove_block(bashrc, self.MARKER_START, self.MARKER_END)
        
        if removed:
            print(f"✅ Removed from {bashrc}")
            print("")
            print("✅ Shell completions uninstalled for bash")
            print("")
            print("Next step: open a new terminal window")
        else:
            print("ℹ️  mdfs completions not found in bash config")
        
        return True
    
    def _uninstall_fish_completions(self) -> bool:
        """Uninstall completions from fish config files."""
        config_files = get_shell_config_files("fish")
        fish_conf_file = config_files["env_files"][0]
        
        removed = remove_block(fish_conf_file, self.MARKER_START, self.MARKER_END)
        
        if removed:
            print(f"✅ Removed from {fish_conf_file}")
            print("")
            print("✅ Shell completions uninstalled for fish")
            print("")
            print("Next step: open a new fish shell")
        else:
            print("ℹ️  mdfs completions not found in fish config")
        
        return True
    
    def execute(self) -> int:
        """Execute the setup command.
        
        Installs or uninstalls shell completions based on args.
        If no args provided, auto-detects and asks for confirmation.
        
        Returns:
            0 on success, 1 on failure
        """
        # If explicit flags are provided, use them
        if self.args.install_completions:
            success = self.install_completions()
        elif self.args.uninstall_completions:
            success = self.uninstall_completions()
        else:
            # Auto-detect: check if completions are already installed
            success = self._auto_detect_and_ask()
        
        return 0 if success else 1
    
    def _auto_detect_and_ask(self) -> bool:
        """Auto-detect completion status and ask user for confirmation.
        
        Returns:
            True if operation succeeded or was cancelled, False otherwise
        """
        config_files = get_shell_config_files(self.shell_type)
        
        # Check if completions are already installed by looking for markers
        completions_installed = False
        
        if self.shell_type == "zsh":
            zshrc = config_files["rc_files"][0]
            if zshrc.exists():
                content = zshrc.read_text(encoding="utf-8")
                completions_installed = self.MARKER_START in content
        elif self.shell_type == "bash":
            bashrc = config_files["rc_files"][0]
            if bashrc.exists():
                content = bashrc.read_text(encoding="utf-8")
                completions_installed = self.MARKER_START in content
        elif self.shell_type == "fish":
            fish_conf = config_files["env_files"][0]
            if fish_conf.exists():
                content = fish_conf.read_text(encoding="utf-8")
                completions_installed = self.MARKER_START in content
        
        if self.shell_type == "unknown":
            print(
                "Error: could not detect your shell.",
                file=sys.stderr,
            )
            print(
                "Supported shells: zsh, bash, fish",
                file=sys.stderr,
            )
            return False
        
        # Ask user what to do
        if completions_installed:
            action = input(f"Shell completions already installed for {self.shell_type}. Uninstall? (y/n): ")
            if action.lower() == "y":
                return self.uninstall_completions()
            else:
                print("Cancelled.", file=sys.stderr)
                return True
        else:
            action = input(f"Install shell completions for {self.shell_type}? (y/n): ")
            if action.lower() == "y":
                return self.install_completions()
            else:
                print("Cancelled.", file=sys.stderr)
                return True
