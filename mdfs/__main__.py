"""
MDFS command-line interface.

Commands:
    init     — initialize .mdfs directory structure
    bundle   — collect project files into a single Markdown context file
    paste    — create a response file from clipboard content
    extract  — write file blocks to disk, apply patch blocks
    log      — show chronological history
"""

from __future__ import annotations

import argparse
import datetime
import platform
import re
import subprocess
import sys
from pathlib import Path

from .bundler import bundle
from .extractor import extract


# ── Naming helpers ──────────────────────────────────────────────────

def _timestamp() -> str:
    return datetime.datetime.now().strftime("%Y-%m-%d_%H%M%S")


def _sanitize_label(label: str) -> str:
    label = label.strip().lower()
    label = label.replace(" ", "_")
    label = re.sub(r"[^\w\-]", "", label)
    label = re.sub(r"_+", "_", label)
    label = label.strip("_")
    return label


def _make_filename(label: str | None) -> str:
    ts = _timestamp()
    if label:
        safe = _sanitize_label(label)
        if safe:
            return f"{ts}__{safe}.md"
    return f"{ts}.md"


# ── .mdfs directory helpers ─────────────────────────────────────────

def _find_mdfs_root(start: str | Path | None = None) -> Path:
    current = Path(start) if start else Path.cwd()
    current = current.resolve()
    while True:
        if (current / ".mdfs").is_dir():
            return current
        parent = current.parent
        if parent == current:
            print(
                "Error: .mdfs directory not found. Run `mdfs init` first.",
                file=sys.stderr,
            )
            sys.exit(1)
        current = parent


def _mdfs_dir(root: Path) -> Path:
    return root / ".mdfs"


def _rules_dir(root: Path) -> Path:
    return _mdfs_dir(root) / "rules"


def _contexts_dir(root: Path) -> Path:
    return _mdfs_dir(root) / "contexts"


def _responses_dir(root: Path) -> Path:
    return _mdfs_dir(root) / "responses"


# ── Clipboard ───────────────────────────────────────────────────────

def _get_clipboard() -> str:
    system = platform.system()

    if system == "Darwin":
        result = subprocess.run(
            ["pbpaste"], capture_output=True, text=True, check=True,
        )
        return result.stdout

    if system == "Linux":
        for cmd in (
            ["xclip", "-selection", "clipboard", "-o"],
            ["xsel", "--clipboard", "--output"],
        ):
            try:
                result = subprocess.run(
                    cmd, capture_output=True, text=True, check=True,
                )
                return result.stdout
            except FileNotFoundError:
                continue
        print(
            "Error: install xclip or xsel for clipboard support on Linux.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Error: clipboard not supported on {system}.", file=sys.stderr)
    sys.exit(1)


# ── Commands ────────────────────────────────────────────────────────

def cmd_init(args: argparse.Namespace) -> None:
    root = Path(args.dir).resolve()
    mdfs = root / ".mdfs"

    for subdir in ("rules", "contexts", "responses"):
        (mdfs / subdir).mkdir(parents=True, exist_ok=True)

    # Write default system prompt
    prompt_path = mdfs / "rules" / "mdfs-system.md"
    if not prompt_path.exists():
        from .default_system_prompt import DEFAULT_SYSTEM_PROMPT

        prompt_path.write_text(DEFAULT_SYSTEM_PROMPT, encoding="utf-8")
        print(f"  📝 Created {prompt_path.relative_to(root)}")

    # Write .gitignore
    gitignore = mdfs / ".gitignore"
    if not gitignore.exists():
        gitignore.write_text(
            "# Keep rules in git, ignore generated content\n"
            "contexts/\n"
            "responses/\n",
            encoding="utf-8",
        )

    print(f"✅ Initialized .mdfs in {root}")


def cmd_bundle(args: argparse.Namespace) -> None:
    root = _find_mdfs_root(args.dir)

    system_prompt = None
    if args.system_prompt:
        system_prompt = Path(args.system_prompt).read_text(encoding="utf-8")
    else:
        default_prompt = _rules_dir(root) / "mdfs-system.md"
        if default_prompt.exists():
            system_prompt = default_prompt.read_text(encoding="utf-8")

    result = bundle(
        base_dir=root,
        file_paths=args.files,
        system_prompt=system_prompt,
    )

    if args.output:
        out_path = Path(args.output)
    else:
        filename = _make_filename(args.label)
        out_path = _contexts_dir(root) / filename

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(result, encoding="utf-8")
    print(f"  📦 Context saved: {out_path.relative_to(root)}", file=sys.stderr)


def cmd_paste(args: argparse.Namespace) -> None:
    root = _find_mdfs_root(args.dir)

    content = _get_clipboard()
    if not content.strip():
        print("Error: clipboard is empty.", file=sys.stderr)
        sys.exit(1)

    filename = _make_filename(args.label)
    out_path = _responses_dir(root) / filename

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(content, encoding="utf-8")

    from .parser import parse, split_files_and_patches

    blocks = parse(content)
    files, patches = split_files_and_patches(blocks)

    print(f"  📋 Response saved: {out_path.relative_to(root)}", file=sys.stderr)
    print(
        f"     {len(files)} file(s), {len(patches)} patch(es) detected",
        file=sys.stderr,
    )

    if args.extract:
        print("  Extracting...", file=sys.stderr)
        from .extractor import extract as do_extract

        actions = do_extract(content, base_dir=root, dry_run=args.dry_run)
        _print_actions(actions)

        errors = [a for a in actions if a.action == "error"]
        if errors:
            print(f"\n  {len(errors)} error(s) occurred.", file=sys.stderr)
            sys.exit(1)


def cmd_extract(args: argparse.Namespace) -> None:
    root = _find_mdfs_root(args.dir)

    md_text = Path(args.input).read_text(encoding="utf-8")
    actions = extract(md_text, base_dir=root, dry_run=args.dry_run)
    _print_actions(actions)

    errors = [a for a in actions if a.action == "error"]
    if errors:
        print(f"\n  {len(errors)} error(s) occurred.", file=sys.stderr)
        sys.exit(1)


def cmd_log(args: argparse.Namespace) -> None:
    root = _find_mdfs_root(args.dir)

    entries: list[tuple[str, str]] = []

    for p in sorted(_contexts_dir(root).glob("*.md")):
        entries.append((p.name, "context"))

    for p in sorted(_responses_dir(root).glob("*.md")):
        entries.append((p.name, "response"))

    entries.sort(key=lambda e: e[0])

    if not entries:
        print("  No contexts or responses yet.")
        return

    icons = {"context": "📦", "response": "📋"}
    for filename, entry_type in entries:
        icon = icons.get(entry_type, "?")
        stem = filename.removesuffix(".md")
        print(f"  {icon} {entry_type:8s}  {stem}")


# ── Helpers ─────────────────────────────────────────────────────────

def _print_actions(actions: list) -> None:
    for action in actions:
        icon = {"write": "📄", "patch": "🩹", "error": "❌"}.get(
            action.action, "?",
        )
        detail = f" — {action.detail}" if action.detail else ""
        print(f"  {icon} {action.action:6s} {action.path}{detail}")


# ── Main ────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        prog="mdfs",
        description="MDFS — Markdown FileSystem tools",
    )
    parser.add_argument(
        "-d", "--dir", default=".",
        help="Project directory (default: current)",
    )
    sub = parser.add_subparsers(dest="command", required=True)

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

    args = parser.parse_args()

    commands = {
        "init": cmd_init,
        "bundle": cmd_bundle,
        "paste": cmd_paste,
        "extract": cmd_extract,
        "log": cmd_log,
    }
    commands[args.command](args)


if __name__ == "__main__":
    main()
