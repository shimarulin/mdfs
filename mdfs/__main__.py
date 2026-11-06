"""
MDFS command-line interface.

Commands:
    init     — initialize .mdfs directory structure
    bundle   — collect rules and/or project files into a Markdown context file
    paste    — create a response file from clipboard content
    extract  — write file blocks to disk, apply patch blocks
    log      — show chronological history
    setup    — install/uninstall shell completions
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from .commands import (
    BundleCommand,
    ExtractCommand,
    InitCommand,
    LogCommand,
    PasteCommand,
    SetupCommand,
)
from .utils import timestamp


def _get_version() -> str:
    """Read version from package metadata or pyproject.toml.
    
    Tries multiple sources in order:
    1. importlib.metadata (for installed packages)
    2. pyproject.toml (for development/editable installs)
    
    Returns "unknown" if version cannot be determined.
    """
    # Try importlib.metadata first (works for installed packages)
    try:
        from importlib.metadata import version
        return version("mdfs")
    except Exception:
        pass

    # Fallback: read pyproject.toml (for development)
    try:
        toml_path = Path(__file__).parent.parent / "pyproject.toml"
        if toml_path.exists():
            content = toml_path.read_text(encoding="utf-8")
            match = re.search(r'version\s*=\s*"([^"]+)"', content)
            if match:
                return match.group(1)
    except Exception:
        pass

    return "unknown"


# Shared parent for the directory overrides: accepted both before and
# after the subcommand (`mdfs --rules-dir X bundle ...` and
# `mdfs bundle --rules-dir X ...` both work).
def _make_overrides_parent() -> argparse.ArgumentParser:
    parent = argparse.ArgumentParser(add_help=False)
    # SUPPRESS keeps the main-parser value intact when the subparser
    # (same parent) does not see the flag: without it, subparser defaults
    # would clobber `mdfs --rules-dir X bundle ...` with None.
    parent.add_argument(
        "--contexts-dir", default=argparse.SUPPRESS,
        help="Override contexts directory (overrides .mdfsrc.yaml)",
    )
    parent.add_argument(
        "--responses-dir", default=argparse.SUPPRESS,
        help="Override responses directory (overrides .mdfsrc.yaml)",
    )
    parent.add_argument(
        "--rules-dir", default=argparse.SUPPRESS,
        help="Override rules directory (overrides .mdfsrc.yaml)",
    )
    return parent


def build_parser() -> argparse.ArgumentParser:
    """Build the mdfs argument parser.

    The directory overrides (`--contexts-dir`, `--responses-dir`,
    `--rules-dir`) are accepted both before and after the subcommand:
    `mdfs --rules-dir X bundle ...` and `mdfs bundle --rules-dir X ...`.
    """
    overrides = _make_overrides_parent()
    parser = argparse.ArgumentParser(
        prog="mdfs",
        description="MDFS — Markdown FileSystem tools",
        parents=[overrides],
    )
    parser.add_argument(
        "-v", "--version", action="version",
        version=f"%(prog)s {_get_version()}",
    )
    parser.add_argument(
        "-d", "--dir", default=".",
        help="Project directory (default: current)",
    )
    sub = parser.add_subparsers(dest="command", required=False)

    sub.add_parser("init", help="Initialize .mdfs directory",
                   parents=[overrides])

    p_bundle = sub.add_parser(
        "bundle", help="Bundle rules and/or files into context.md",
        parents=[overrides],
    )
    p_bundle.add_argument("files", nargs="*",
                          help="Project-relative file paths or directories "
                               "(optional: without files, bundles only the rules)")
    p_bundle.add_argument("-l", "--label", help="Label for the context file")
    p_bundle.add_argument("-s", "--system-prompt", help="System prompt file")
    p_bundle.add_argument("-o", "--output", help="Custom output path")
    p_bundle.add_argument("-q", "--query", help="User question to append to the bundle")
    p_bundle.add_argument("--clip", action="store_true",
                          help="Also copy the bundle to clipboard")
    p_bundle.add_argument("--rules", action="append", metavar="GLOB",
                          help="Additional rules to include, by filename globs "
                               "(comma-separated or repeated, e.g. --rules '00-*,1*'; "
                               "'*' = all). Default: config 'rules_always'")
    p_bundle.add_argument("--no-preamble", action="store_true",
                          help="Disable preamble and table of contents")
    p_bundle.add_argument("--no-gitignore", action="store_true",
                          help="Include files that are in .gitignore")

    p_paste = sub.add_parser("paste", help="Save clipboard as response",
                             parents=[overrides])
    p_paste.add_argument("label", nargs="?", default=None,
                         help="Label for the response file (optional)")
    p_paste.add_argument("-x", "--extract", action="store_true",
                         help="Also extract files and apply patches")
    p_paste.add_argument("--dry-run", action="store_true")

    p_extract = sub.add_parser("extract", help="Extract files from Markdown",
                               parents=[overrides])
    p_extract.add_argument("input",
                           help="Input Markdown file")
    p_extract.add_argument("--dry-run", action="store_true")
    p_extract.add_argument("-f", "--force", action="store_true",
                           help="Force overwrite all existing files")

    sub.add_parser("log", help="Show chronological log", parents=[overrides])

    p_setup = sub.add_parser("setup", help="Install/uninstall shell completions",
                             parents=[overrides])
    p_setup.add_argument(
        "-i", "--install-completions",
        action="store_true",
        help="Install shell completions for current shell",
    )
    p_setup.add_argument(
        "-u", "--uninstall-completions",
        action="store_true",
        help="Uninstall shell completions",
    )

    return parser


def main() -> None:
    """Parse arguments and dispatch to appropriate command."""
    parser = build_parser()
    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # Map command names to command classes
    commands = {
        "init": InitCommand,
        "bundle": BundleCommand,
        "paste": PasteCommand,
        "extract": ExtractCommand,
        "log": LogCommand,
        "setup": SetupCommand,
    }

    # Get the command class and instantiate it
    command_class = commands[args.command]
    command = command_class(args)
    
    # Execute the command and exit with its return code
    exit_code = command.execute()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
