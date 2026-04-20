"""Fuzzy patch applier for LLM-generated unified diffs."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass
class DiffLine:
    type: str
    text: str


@dataclass
class Hunk:
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffLine]


class PatchError(Exception):
    pass


_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@")


def parse_hunks(diff_text: str) -> list[Hunk]:
    lines = diff_text.split("\n")
    hunks: list[Hunk] = []
    current_hunk: Hunk | None = None

    for line in lines:
        if line.startswith("--- ") or line.startswith("+++ "):
            continue
        hunk_match = _HUNK_RE.match(line)
        if hunk_match:
            if current_hunk is not None:
                hunks.append(current_hunk)
            current_hunk = Hunk(
                old_start=int(hunk_match.group(1)),
                old_count=int(hunk_match.group(2) or "1"),
                new_start=int(hunk_match.group(3)),
                new_count=int(hunk_match.group(4) or "1"),
                lines=[],
            )
            continue
        if current_hunk is None:
            continue
        if line.startswith("+"):
            current_hunk.lines.append(DiffLine("+", line[1:]))
        elif line.startswith("-"):
            current_hunk.lines.append(DiffLine("-", line[1:]))
        elif line.startswith(" "):
            current_hunk.lines.append(DiffLine(" ", line[1:]))
        elif line == "":
            current_hunk.lines.append(DiffLine(" ", ""))

    if current_hunk is not None:
        hunks.append(current_hunk)
    return hunks


def _context_and_removals(hunk: Hunk) -> list[str]:
    return [dl.text for dl in hunk.lines if dl.type in (" ", "-")]


def _find_match(
    file_lines: list[str], pattern: list[str], hint_start: int,
) -> int | None:
    if not pattern:
        return max(0, hint_start - 1)

    n = len(file_lines)
    plen = len(pattern)

    def exact_at(pos: int) -> bool:
        if pos < 0 or pos + plen > n:
            return False
        return all(file_lines[pos + j] == pattern[j] for j in range(plen))

    def stripped_at(pos: int) -> bool:
        if pos < 0 or pos + plen > n:
            return False
        return all(
            file_lines[pos + j].rstrip() == pattern[j].rstrip()
            for j in range(plen)
        )

    hint = max(0, hint_start - 1)

    # Try exact match at hint position first
    if exact_at(hint):
        return hint

    # Search expanding outward from hint position
    for delta in range(1, n):
        for pos in (hint - delta, hint + delta):
            if 0 <= pos <= n - plen and exact_at(pos):
                return pos
        if hint - delta < 0 and hint + delta >= n:
            break

    # Try with stripped whitespace
    for delta in range(0, n):
        for pos in (hint - delta, hint + delta):
            if 0 <= pos <= n - plen and stripped_at(pos):
                return pos
        if hint - delta < 0 and hint + delta >= n:
            break

    # Additional search: try with leading/trailing whitespace stripped
    for i in range(n - plen + 1):
        if all(
            file_lines[i + j].strip() == pattern[j].strip()
            for j in range(plen)
        ):
            return i

    # Last resort: fuzzy search with partial matching
    # This helps when context lines have minor differences
    for i in range(n - plen + 1):
        matches = 0
        for j in range(plen):
            if file_lines[i + j].rstrip() == pattern[j].rstrip():
                matches += 1
        # If we have a high match ratio, consider it a match
        if matches >= max(1, plen * 0.6):  # Lower threshold to 60% for better matching
            return i

    return None


def apply_patch(original: str, diff_text: str) -> str:
    hunks = parse_hunks(diff_text)
    if not hunks:
        return original

    file_lines = original.split("\n")
    offset = 0

    for i, hunk in enumerate(hunks):
        old_side = _context_and_removals(hunk)
        match_pos = _find_match(file_lines, old_side, hunk.old_start + offset)
        if match_pos is None:
            raise PatchError(
                f"Hunk {i + 1}: cannot find context in file. "
                f"Expected (first 3 lines): {old_side[:3]!r}"
            )
        new_lines = [dl.text for dl in hunk.lines if dl.type in (" ", "+")]
        old_len = len(old_side)
        file_lines[match_pos : match_pos + old_len] = new_lines
        offset += len(new_lines) - old_len

    return "\n".join(file_lines)
