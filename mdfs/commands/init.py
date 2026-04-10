"""Initialize .mdfs directory structure."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from ..config import Config
from .base import BaseCommand


class InitCommand(BaseCommand):
    """Command for initializing .mdfs directory structure."""

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
        
        Creates .mdfs directory structure with .gitignore and .mdfsrc.yaml config.
        
        Returns:
            Exit code (0 for success)
        """
        mdfs = self.root / ".mdfs"

        for subdir in ("contexts", "responses"):
            (mdfs / subdir).mkdir(parents=True, exist_ok=True)

        # Write .gitignore
        gitignore = mdfs / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text(
                "# Ignore generated content\n"
                "contexts/\n"
                "responses/\n",
                encoding="utf-8",
            )

        # Create .mdfsrc.yaml config file
        config_path = self.root / ".mdfsrc.yaml"
        if not config_path.exists():
            Config.create_default_config(config_path)

        print(f"✅ Initialized .mdfs in {self.root}")
        print(f"✅ Created .mdfsrc.yaml config file")
        return 0
