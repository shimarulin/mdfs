"""Paste LLM response from clipboard into a response file."""

from __future__ import annotations

import sys
from argparse import Namespace

from ..extractor import extract as do_extract
from ..parser import parse, split_files_and_patches
from ..utils import get_clipboard, make_filename, print_actions, responses_dir
from .base import BaseCommand


class PasteCommand(BaseCommand):
    """Command for saving clipboard content as a response file."""

    def execute(self) -> int:
        """Execute the paste command.
        
        Saves clipboard content as a response file and optionally
        extracts files and applies patches.
        
        Returns:
            Exit code (0 for success, 1 for failure)
        """
        content = get_clipboard()
        
        filename = make_filename(self.args.label)
        out_path = responses_dir(self.root) / filename

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

        # Check if clipboard is empty
        if not content.strip():
            print("Error: clipboard is empty.", file=sys.stderr)
            # Return 1 if not extracting
            if not self.args.extract:
                return 1
            return 0

        blocks = parse(content)
        files, patches = split_files_and_patches(blocks)

        print(
            f"  📋 Response saved: {out_path.relative_to(self.root)}",
            file=sys.stderr,
        )
        print(
            f"     {len(files)} file(s), {len(patches)} patch(es) detected",
            file=sys.stderr,
        )

        if self.args.extract:
            print("  Extracting...", file=sys.stderr)
            actions = do_extract(
                content, base_dir=self.root, dry_run=self.args.dry_run
            )
            print_actions(actions)

            errors = [a for a in actions if a.action == "error"]
            if errors:
                print(
                    f"\n  {len(errors)} error(s) occurred.",
                    file=sys.stderr,
                )
                return 1

        return 0
