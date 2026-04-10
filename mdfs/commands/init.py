"""Initialize project configuration."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from ..config import Config
from .base import BaseCommand


class InitCommand(BaseCommand):
    """Command for initializing project configuration."""

    def __init__(self, args: Namespace):
        """Initialize the init command.
        
        Args:
            args: Parsed command-line arguments
        """
        # Init command doesn't need find_mdfs_root, override initialization
        self.args = args
        self.root = Path(args.dir).resolve() if args.dir else Path.cwd()

    def execute(self) -> int:
        """Execute the init command.
        
        Creates .mdfsrc.yaml config file in the project directory.
        Directories for contexts, responses, and rules are created automatically
        when needed by bundle, paste, and other commands.
        
        Returns:
            Exit code (0 for success)
        """
        # Create .mdfsrc.yaml config file
        config_path = self.root / ".mdfsrc.yaml"
        if not config_path.exists():
            Config.create_default_config(config_path)
            print(f"✅ Created .mdfsrc.yaml config file in {self.root}")
        else:
            print(f"⚠️  .mdfsrc.yaml already exists in {self.root}")
        return 0
