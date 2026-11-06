"""Deprecated alias for the rules-only bundle.

`mdfs rules` builds the same document as `mdfs bundle` without file
arguments (preamble + rules block + persistence footer), prints it to
stdout and copies it to the clipboard. Kept for backward compatibility
with mdfs <= 0.6.x; will be removed in 0.8.0 — use
`mdfs bundle` (no file arguments; add `--clip`) instead.
"""

from __future__ import annotations

import sys
from argparse import Namespace

from ..config import Config
from ..core.bundler import bundle
from ..core.rules import resolve_rules
from ..utils import copy_to_clipboard
from .base import BaseCommand

DEPRECATION_NOTICE = (
    "⚠️  'mdfs rules' is deprecated and will be removed in 0.8.0 — "
    "use 'mdfs bundle' (no file arguments; add --clip) instead."
)


class RulesCommand(BaseCommand):
    """Deprecated alias: print and copy the rules-only bundle document.

    Produces exactly the same document as ``mdfs bundle`` without file
    arguments (rules selected by config ``rules_always`` globs, packaged
    file output format rule as fallback), so there is a single rules
    pipeline behind the CLI.
    """

    def execute(self) -> int:
        """Execute the deprecated rules command.

        Prints the deprecation notice, builds the rules-only document
        (same as `mdfs bundle` without files), prints it to stdout and
        copies it to the clipboard.

        Returns:
            Exit code (0 for success)
        """
        print(DEPRECATION_NOTICE, file=sys.stderr)

        # Load configuration (same fallback as BundleCommand)
        try:
            config = Config()
        except Exception as e:
            print(f"Error loading configuration: {e}", file=sys.stderr)
            config = Config.__new__(Config)
            config.config_path = None
            config.config_data = {}

        self.apply_config_overrides(config)

        rules = resolve_rules(
            config.get_rules_dir(self.root), list(config.get_rules_always())
        )
        result = bundle(
            base_dir=self.root,
            file_paths=[],
            rules=rules,
        )

        # Document to stdout first, so it is available even if the
        # clipboard tool is missing (copy_to_clipboard exits in that case)
        print(result)
        try:
            copy_to_clipboard(result)
            print("\n✅ Copied to clipboard", file=sys.stderr)
        except SystemExit:
            raise

        return 0
