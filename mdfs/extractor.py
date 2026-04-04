"""MDFS extractor — writes file blocks to disk, applies patch blocks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .parser import BlockType, parse, split_files_and_patches
from .patcher import PatchError, apply_patch


@dataclass
class Action:
    action: str  # "write", "patch", "error"
    path: str
    detail: str = ""


def extract(
    markdown_text: str,
    base_dir: str | Path,
    dry_run: bool = False,
) -> list[Action]:
    base = Path(base_dir)
    blocks = parse(markdown_text)
    files, patches = split_files_and_patches(blocks)
    actions: list[Action] = []

    for block in files:
        target = base / block.path
        if dry_run:
            actions.append(Action("write", block.path, f"({len(block.content)} bytes)"))
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(block.content + "\n", encoding="utf-8")
        actions.append(Action("write", block.path))

    for block in patches:
        target = base / block.path
        if not target.is_file():
            actions.append(Action("error", block.path, "Cannot patch: file does not exist"))
            continue
        original = target.read_text(encoding="utf-8")
        try:
            patched = apply_patch(original, block.content)
        except PatchError as e:
            actions.append(Action("error", block.path, str(e)))
            continue
        if dry_run:
            actions.append(Action("patch", block.path, "(dry-run)"))
            continue
        target.write_text(patched, encoding="utf-8")
        actions.append(Action("patch", block.path))

    return actions
