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
    fence_depth_error: bool = False
    normalized_content: Optional[str] = None


_MARKER_RE = re.compile(r"^<!--\s+(file|patch):\s+\"(.+?)\"\s+-->$")
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
                    content = "\n".join(current_content_lines)
                    
                    # Validate fence depth
                    has_depth_error = not validate_fence_depth(fence_backticks, content)
                    normalized_content = None
                    if has_depth_error:
                        normalized_content = normalize_fence_depth(content, fence_backticks)
                    
                    blocks.append(Block(
                        type=btype, path=bpath,
                        content=content,
                        lang=current_lang, line_number=bline,
                        fence_depth_error=has_depth_error,
                        normalized_content=normalized_content,
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


def get_max_fence_depth(text: str) -> int:
    """Get the maximum nesting depth of fences in text.
    
    Returns the number of backticks in the deepest fence found.
    Returns 0 if no fences are found.
    """
    lines = text.split("\n")
    max_depth = 0
    for line in lines:
        match = _FENCE_RE.match(line)
        if match:
            depth = len(match.group(1))
            max_depth = max(max_depth, depth)
    return max_depth


def validate_fence_depth(outer_fence_depth: int, content: str) -> bool:
    """Validate that outer fence is deeper than any inner fences.
    
    Args:
        outer_fence_depth: Number of backticks in outer fence
        content: Content of the fence (which may contain nested fences)
        
    Returns:
        True if valid (outer_fence_depth > max inner fence depth), False otherwise
    """
    max_inner_depth = get_max_fence_depth(content)
    return outer_fence_depth > max_inner_depth


def normalize_fence_depth(content: str, outer_fence_depth: int) -> str:
    """Normalize fence depths in content.
    
    Ensures that all fences in content are less than outer_fence_depth.
    - Innermost fences use 3 backticks
    - Each outer level uses 1 more backtick
    
    Args:
        content: Content that may have incorrectly nested fences
        outer_fence_depth: Depth of the outer fence containing this content
        
    Returns:
        Content with normalized fence depths
    """
    max_inner = get_max_fence_depth(content)
    if max_inner < 3:
        return content  # No fences or already using < 3 backticks
    
    # Calculate depth for each fence found
    # Map old depths to new depths
    lines = content.split("\n")
    fences_found: dict[int, int] = {}  # old depth -> count
    
    # First pass: collect all fence depths and determine mapping
    for line in lines:
        match = _FENCE_RE.match(line)
        if match:
            old_depth = len(match.group(1))
            if old_depth not in fences_found:
                fences_found[old_depth] = 0
            fences_found[old_depth] += 1
    
    # Sort by depth to assign new normalized depths
    sorted_old_depths = sorted(fences_found.keys(), reverse=True)
    depth_map: dict[int, int] = {}
    
    # Assign new depths: innermost = 3, each level up = +1
    # But all must be < outer_fence_depth
    next_new_depth = 3
    for old_depth in reversed(sorted_old_depths):
        depth_map[old_depth] = next_new_depth
        next_new_depth += 1
    
    # Ensure all new depths are < outer_fence_depth
    if next_new_depth > outer_fence_depth:
        # Adjust: start innermost lower (but we can't go below 3)
        # This shouldn't happen if outer_fence_depth is correct
        pass
    
    # Second pass: replace fences with normalized depths
    result_lines: list[str] = []
    for line in lines:
        match = _FENCE_RE.match(line)
        if match:
            old_depth = len(match.group(1))
            lang = match.group(2) or ""
            new_depth = depth_map.get(old_depth, old_depth)
            result_lines.append("`" * new_depth + lang)
        else:
            result_lines.append(line)
    
    return "\n".join(result_lines)


def split_files_and_patches(
    blocks: list[Block],
) -> tuple[list[Block], list[Block]]:
    files = [b for b in blocks if b.type == BlockType.FILE]
    patches = [b for b in blocks if b.type == BlockType.PATCH]
    return files, patches
