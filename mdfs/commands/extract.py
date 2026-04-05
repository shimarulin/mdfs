"""Extract files and apply patches from Markdown."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from ..extractor import extract as do_extract
from ..utils import print_actions
from .base import BaseCommand


class ExtractCommand(BaseCommand):
    """Command for extracting files and applying patches from Markdown."""

    def execute(self) -> int:
        """Execute the extract command.
        
        Extracts files and applies patches from a Markdown document.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        md_text = Path(self.args.input).read_text(encoding="utf-8")
        actions = do_extract(
            md_text, base_dir=self.root, dry_run=self.args.dry_run
        )
        print_actions(actions)

        errors = [a for a in actions if a.action == "error"]
        if errors:
            print(f"\n  {len(errors)} error(s) occurred.", file=sys.stderr)
            return 1

        return 0
