"""Display and copy system prompt rules to clipboard."""

from __future__ import annotations

from argparse import Namespace

from ..default_system_prompt import DEFAULT_SYSTEM_PROMPT
from ..utils import copy_to_clipboard
from .base import BaseCommand


class RulesCommand(BaseCommand):
    """Command for displaying system prompt rules and copying to clipboard."""

    def __init__(self, args: Namespace):
        """Initialize the rules command.
        
        Args:
            args: Parsed command-line arguments
        """
        # Rules command doesn't need find_mdfs_root, override initialization
        self.args = args

    def execute(self) -> int:
        """Execute the rules command.
        
        Prints the default system prompt to console and copies it to clipboard.
        
        Returns:
            Exit code (0 for success)
        """
        # Print to console
        print(DEFAULT_SYSTEM_PROMPT)
        
        # Copy to clipboard
        try:
            copy_to_clipboard(DEFAULT_SYSTEM_PROMPT)
            print("\n✅ System prompt copied to clipboard", file=__import__("sys").stderr)
        except SystemExit:
            # If copy fails due to missing clipboard tool, we already printed
            # the prompt, so that's still useful
            raise
        
        return 0
