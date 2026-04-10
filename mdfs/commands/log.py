"""Show chronological history of contexts and responses."""

from __future__ import annotations

import sys
from argparse import Namespace

from ..config import Config
from .base import BaseCommand


class LogCommand(BaseCommand):
    """Command for showing chronological history of contexts and responses."""

    def execute(self) -> int:
        """Execute the log command.
        
        Displays a chronological list of all contexts and responses.
        
        Returns:
            Exit code (0 for success)
        """
        # Load configuration
        try:
            config = Config()
        except Exception as e:
            print(f"Error loading configuration: {e}", file=sys.stderr)
            config = Config.__new__(Config)
            config.config_path = None
            config.config_data = {}

        # Apply command-line config overrides
        self.apply_config_overrides(config)

        entries: list[tuple[str, str]] = []

        contexts_path = config.get_contexts_dir(self.root)
        if contexts_path.exists():
            for p in sorted(contexts_path.glob("*.md")):
                entries.append((p.name, "context"))

        responses_path = config.get_responses_dir(self.root)
        if responses_path.exists():
            for p in sorted(responses_path.glob("*.md")):
                entries.append((p.name, "response"))

        entries.sort(key=lambda e: e[0])

        if not entries:
            print("  No contexts or responses yet.")
            return 0

        icons = {"context": "📦", "response": "📋"}
        for filename, entry_type in entries:
            icon = icons.get(entry_type, "?")
            stem = filename.removesuffix(".md")
            print(f"  {icon} {entry_type:8s}  {stem}")

        return 0
