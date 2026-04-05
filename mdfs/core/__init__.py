"""Core MDFS functionality — bundling, parsing, extracting, and patching."""

from .bundler import bundle
from .extractor import extract
from .parser import parse, split_files_and_patches
from .patcher import apply_patch

__all__ = [
    "bundle",
    "extract",
    "parse",
    "split_files_and_patches",
    "apply_patch",
]
