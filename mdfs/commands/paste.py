"""Paste LLM response from clipboard into a response file."""

from __future__ import annotations

import sys
from argparse import Namespace

from ..config import Config
from ..core.extractor import extract as do_extract
from ..core.parser import parse, split_files_and_patches
from ..utils import get_clipboard, make_filename, print_actions
from .base import BaseCommand


class PasteCommand(BaseCommand):
    """Command for saving clipboard content as a response file."""

    def execute(self) -> int:
        """Execute the paste command.
        
        Reads clipboard content and saves it as a response file.
        Optionally extracts files and applies patches if --extract flag is set.
        
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

        content = get_clipboard()
        
        # Check if clipboard is empty before processing
        if not content.strip():
            print("Error: clipboard is empty.", file=sys.stderr)
            # Return 1 if not extracting
            if not self.args.extract:
                return 1
            # If extracting with empty clipboard, return 0
            return 0
        
        filename = make_filename(self.args.label)
        out_path = config.get_responses_dir(self.root) / filename

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

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
