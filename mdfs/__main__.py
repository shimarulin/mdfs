"""
MDFS command-line interface.

Commands:
    init     — initialize .mdfs directory structure
    bundle   — collect project files into a single Markdown context file
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


def main() -> None:
    """Parse arguments and dispatch to appropriate command."""
    parser = argparse.ArgumentParser(
        prog="mdfs",
        description="MDFS — Markdown FileSystem tools",
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

    sub.add_parser("init", help="Initialize .mdfs directory")

    p_bundle = sub.add_parser("bundle", help="Bundle files into context.md")
    p_bundle.add_argument("-f", "--files", nargs="+", required=True,
                          help="Project-relative file paths")
    p_bundle.add_argument("-l", "--label", help="Label for the context file")
    p_bundle.add_argument("-s", "--system-prompt", help="System prompt file")
    p_bundle.add_argument("-o", "--output", help="Custom output path")

    p_paste = sub.add_parser("paste", help="Save clipboard as response")
    p_paste.add_argument("-l", "--label", help="Label for the response file")
    p_paste.add_argument("-x", "--extract", action="store_true",
                         help="Also extract files and apply patches")
    p_paste.add_argument("--dry-run", action="store_true")

    p_extract = sub.add_parser("extract", help="Extract files from Markdown")
    p_extract.add_argument("-i", "--input", required=True,
                           help="Input Markdown file")
    p_extract.add_argument("--dry-run", action="store_true")

    sub.add_parser("log", help="Show chronological log")

    p_setup = sub.add_parser("setup", help="Install/uninstall shell completions")
    p_setup_group = p_setup.add_mutually_exclusive_group(required=False)
    p_setup_group.add_argument(
        "-i", "--install-completions",
        action="store_true",
        help="Install shell completions for current shell",
    )
    p_setup_group.add_argument(
        "-u", "--uninstall-completions",
        action="store_true",
        help="Uninstall shell completions",
    )

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
