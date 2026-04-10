"""Base class for all MDFS commands."""

from __future__ import annotations

import sys
from abc import ABC, abstractmethod
from argparse import Namespace
from pathlib import Path

from ..config import Config
from ..utils import find_mdfs_root


class BaseCommand(ABC):
    """Abstract base class for all MDFS commands.
    
    Provides common functionality for command execution and error handling.
    """

    def __init__(self, args: Namespace):
        """Initialize the command with parsed arguments.
        
        Args:
            args: Parsed command-line arguments
        """
        self.args = args
        self.root = find_mdfs_root(getattr(args, 'dir', None))

    @abstractmethod
    def execute(self) -> int:
        """Execute the command.
        
        Returns:
            Exit code (0 for success, non-zero for failure)
        """
        pass

    def error(self, message: str, exit_code: int = 1) -> None:
        """Print an error message and exit.
        
        Args:
            message: Error message to display
            exit_code: Exit code (default: 1)
        """
        print(f"Error: {message}", file=sys.stderr)
        sys.exit(exit_code)

    def apply_config_overrides(self, config: Config) -> None:
        """Apply command-line config overrides to the configuration.
        
        Command-line arguments take precedence over config file values.
        
        Args:
            config: Config object to override
        """
        overrides = {
            "contexts_dir": getattr(self.args, "contexts_dir", None),
            "responses_dir": getattr(self.args, "responses_dir", None),
            "prompt_extensions_dirs": getattr(self.args, "prompt_extensions_dirs", None),
        }
        # Remove None values to avoid overriding with None
        overrides = {k: v for k, v in overrides.items() if v is not None}
        if overrides:
            config.override(**overrides)
