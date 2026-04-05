"""Bundle project files into a Markdown context document."""

from __future__ import annotations

from argparse import Namespace
from pathlib import Path

from ..bundler import bundle
from ..utils import contexts_dir, make_filename, rules_dir
from .base import BaseCommand


class BundleCommand(BaseCommand):
    """Command for bundling project files into a single Markdown document."""

    def execute(self) -> int:
        """Execute the bundle command.
        
        Packs specified files into a single Markdown document with
        optional system prompt prepended.
        
        Returns:
            Exit code (0 for success)
        """
        system_prompt = None
        if self.args.system_prompt:
            system_prompt = Path(self.args.system_prompt).read_text(
                encoding="utf-8"
            )
        else:
            default_prompt = rules_dir(self.root) / "mdfs-system.md"
            if default_prompt.exists():
                system_prompt = default_prompt.read_text(encoding="utf-8")

        result = bundle(
            base_dir=self.root,
            file_paths=self.args.files,
            system_prompt=system_prompt,
        )

        if self.args.output:
            out_path = Path(self.args.output)
        else:
            filename = make_filename(self.args.label)
            out_path = contexts_dir(self.root) / filename

        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(result, encoding="utf-8")
        print(
            f"  📦 Context saved: {out_path.relative_to(self.root)}",
            file=__import__("sys").stderr,
        )
        return 0
