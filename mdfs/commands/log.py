"""Show chronological history of contexts and responses."""

from __future__ import annotations

from argparse import Namespace

from ..utils import contexts_dir, responses_dir
from .base import BaseCommand


class LogCommand(BaseCommand):
    """Command for showing chronological history of contexts and responses."""

    def execute(self) -> int:
        """Execute the log command.
        
        Displays a chronological list of all contexts and responses.
        
        Returns:
            Exit code (0 for success)
        """
        entries: list[tuple[str, str]] = []

        for p in sorted(contexts_dir(self.root).glob("*.md")):
            entries.append((p.name, "context"))

        for p in sorted(responses_dir(self.root).glob("*.md")):
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
