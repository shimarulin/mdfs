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


def _prompt_overwrite(path: str) -> str:
    """Prompt user whether to overwrite a file.
    
    Args:
        path: Path to the file
        
    Returns:
        User's choice: 'y', 'n', 'Y', or 'N'
    """
    while True:
        response = input(f"  Overwrite '{path}'? (y)es / (n)o / (Y)es to all / (N)o to all: ").strip()
        if response in ('y', 'n', 'Y', 'N'):
            return response
        print("  Invalid response. Please enter y, n, Y, or N.")


def extract(
    markdown_text: str,
    base_dir: str | Path,
    dry_run: bool = False,
    force: bool = False,
) -> list[Action]:
    """Extract files and apply patches from Markdown text.
    
    Args:
        markdown_text: Markdown content containing file and patch blocks
        base_dir: Base directory for file paths
        dry_run: If True, don't write files or apply patches
        force: If True, overwrite all existing files without prompting
        
    Returns:
        List of Action objects describing what was done
    """
    base = Path(base_dir)
    blocks = parse(markdown_text)
    files, patches = split_files_and_patches(blocks)
    actions: list[Action] = []

    # Check if no markers found
    if not files and not patches:
        actions.append(Action("info", "", "No markers found for extraction"))
        return actions

    # Print preview of files and patches
    if files or patches:
        print("\nFiles to extract:")
        for block in files:
            target = base / block.path
            exists_marker = " [EXISTS]" if target.exists() else ""
            print(f"  - {block.path}{exists_marker}")
        
        if patches:
            print("\nPatches to apply:")
            for block in patches:
                target = base / block.path
                exists_marker = " [EXISTS]" if target.exists() else ""
                print(f"  - {block.path}{exists_marker}")
        print()

    force_all = force
    skip_all = False

    for block in files:
        target = base / block.path
        
        # Use normalized content if fence depth error was detected
        content_to_write = block.normalized_content if block.fence_depth_error else block.content
        detail = ""
        if block.fence_depth_error:
            detail = "(normalized fence depth)"
        
        if dry_run:
            actions.append(Action("write", block.path, f"({len(content_to_write)} bytes) {detail}"))
            continue
        
        # Check if file exists and handle overwrite logic
        if target.exists() and not force_all and not skip_all:
            choice = _prompt_overwrite(block.path)
            if choice == 'y':
                pass  # Proceed with overwrite
            elif choice == 'n':
                actions.append(Action("skip", block.path))
                continue
            elif choice == 'Y':
                force_all = True
                # Proceed with overwrite for this file
            elif choice == 'N':
                skip_all = True
                actions.append(Action("skip", block.path))
                continue
        
        if skip_all:
            actions.append(Action("skip", block.path))
            continue
        
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content_to_write + "\n", encoding="utf-8")
        actions.append(Action("write", block.path, detail))

    # Group patches by file path to apply them in sequence
    patches_by_file: dict[str, list] = {}
    for block in patches:
        path_key = str(block.path)
        if path_key not in patches_by_file:
            patches_by_file[path_key] = []
        patches_by_file[path_key].append(block)

    # Apply patches for each file, chaining them together
    for file_path, file_patches in patches_by_file.items():
        target = base / file_path
        if not target.is_file():
            actions.append(Action("error", file_path, "Cannot patch: file does not exist"))
            continue
        
        # Read file once at the start
        current_content = target.read_text(encoding="utf-8")
        patch_succeeded = True
        
        # Apply all patches to this file in sequence
        for patch_index, block in enumerate(file_patches, 1):
            if dry_run:
                actions.append(Action("patch", file_path, "(dry-run)"))
                continue
            
            try:
                current_content = apply_patch(current_content, block.content)
            except PatchError as e:
                # If this is not the first patch, indicate it in the error message
                error_msg = str(e)
                if len(file_patches) > 1:
                    error_msg = f"Patch {patch_index}: {error_msg}"
                actions.append(Action("error", file_path, error_msg))
                patch_succeeded = False
                break
        
        # Write file only if all patches succeeded
        if patch_succeeded:
            target.write_text(current_content, encoding="utf-8")
            for _ in file_patches:
                actions.append(Action("patch", file_path))

    return actions
