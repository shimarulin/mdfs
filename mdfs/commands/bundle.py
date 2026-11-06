"""Bundle project rules and/or files into a Markdown context document."""

from __future__ import annotations

import sys
from argparse import Namespace
from pathlib import Path

from ..config import Config
from ..core.bundler import bundle
from ..core.rules import render_rules
from ..utils import copy_to_clipboard, make_filename
from .base import BaseCommand


class BundleCommand(BaseCommand):
    """Command for bundling rules and project files into a Markdown document."""

    def execute(self) -> int:
        """Execute the bundle command.

        Packs .mdfs/rules/ and the specified files into a single Markdown
        document. Without file arguments, produces a rules-only document
        (useful at session start). Optionally appends the user question
        and copies the result to the clipboard.

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

        system_prompt = None
        if self.args.system_prompt:
            system_prompt = Path(self.args.system_prompt).read_text(
                encoding="utf-8"
            )

        # Determine whether to include preamble
        include_preamble = not self.args.no_preamble

        # Load rules from .mdfs/rules/ (--all includes alwaysApply: false)
        include_all = getattr(self.args, "all", False)
        rules = render_rules(self.root, include_all=include_all)
        query = getattr(self.args, "query", None)

        result = bundle(
            base_dir=self.root,
            file_paths=self.args.files,
            system_prompt=system_prompt,
            include_preamble=include_preamble,
            respect_gitignore=not self.args.no_gitignore if hasattr(self.args, "no_gitignore") else True,
            interactive=True,
            rules=rules,
            query=query,
        )

        if self.args.output:
            out_path = Path(self.args.output)
        else:
            filename = make_filename(self.args.label)
            out_path = config.get_contexts_dir(self.root) / filename

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        try:
            display_path = out_path.relative_to(self.root)
        except ValueError:
            display_path = out_path
        print(
            f"  📦 Context saved: {display_path}",
            file=sys.stderr,
        )

        # Optionally copy the bundle to the system clipboard
        if getattr(self.args, "clip", False):
            copy_to_clipboard(result)
            print("  📋 Copied to clipboard", file=sys.stderr)

        return 0
