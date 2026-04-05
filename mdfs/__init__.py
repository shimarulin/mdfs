"""MDFS — Markdown FileSystem: bundle, extract, and patch project files."""

from .core.bundler import bundle
from .core.extractor import extract
from .core.parser import Block, BlockType, parse
from .core.patcher import PatchError, apply_patch

__all__ = [
    "Block",
    "BlockType",
    "PatchError",
    "apply_patch",
    "bundle",
    "extract",
    "parse",
]
