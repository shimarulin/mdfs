"""MDFS parser — extracts file blocks and patch blocks from Markdown."""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BlockType(Enum):
    FILE = "file"
    PATCH = "patch"


@dataclass
class Block:
    type: BlockType
    path: str
    content: str
    lang: str = ""
    description: str = ""
    line_number: int = 0


_MARKER_RE = re.compile(r"^<!--\s+(file|patch):\s+(.+?)\s+-->$")
_FENCE_RE = re.compile(r"^(`{3,})(\S*)?\s*$")


def parse(text: str) -> list[Block]:
    lines = text.split("\n")
    blocks: list[Block] = []

    pending_marker: Optional[tuple[BlockType, str, int]] = None
    in_fence = False
    fence_backticks = 0
    current_content_lines: list[str] = []
    current_lang = ""

    for i, line in enumerate(lines):
        if in_fence:
            m = _FENCE_RE.match(line)
            if m and len(m.group(1)) == fence_backticks and not m.group(2):
                if pending_marker is not None:
                    btype, bpath, bline = pending_marker
                    blocks.append(Block(
                        type=btype, path=bpath,
                        content="\n".join(current_content_lines),
                        lang=current_lang, line_number=bline,
                    ))
                    pending_marker = None
                in_fence = False
                fence_backticks = 0
                current_content_lines = []
                current_lang = ""
            else:
                current_content_lines.append(line)
            continue

        marker_match = _MARKER_RE.match(line.strip())
        if marker_match:
            btype_str, bpath = marker_match.group(1), marker_match.group(2)
            btype = BlockType.FILE if btype_str == "file" else BlockType.PATCH
            pending_marker = (btype, bpath, i + 1)
            continue

        fence_match = _FENCE_RE.match(line)
        if fence_match:
            in_fence = True
            fence_backticks = len(fence_match.group(1))
            current_lang = fence_match.group(2) or ""
            current_content_lines = []
            continue

    return blocks


def split_files_and_patches(
    blocks: list[Block],
) -> tuple[list[Block], list[Block]]:
    files = [b for b in blocks if b.type == BlockType.FILE]
    patches = [b for b in blocks if b.type == BlockType.PATCH]
    return files, patches
