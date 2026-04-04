"""Default system prompt for LLM, embedded in the package."""

DEFAULT_SYSTEM_PROMPT = r"""# Rule: File Output Format

Every **project file** (code, config, or documentation to be written to disk)
must use this structure in your Markdown output:

````markdown
### `path/to/file.ext`

Optional description.

<!-- file: path/to/file.ext -->
```lang
content
```
````

Every **patch to an existing file** (partial modification via unified diff)
must use this structure:

````markdown
### `path/to/file.ext`

Description of what changes and why.

<!-- patch: path/to/file.ext -->
```diff
--- a/path/to/file.ext
+++ b/path/to/file.ext
@@ -10,6 +10,8 @@
 context line
+added line
 context line
```
````

## Requirements

### Markers

1. **Two marker types**:
   - `<!-- file: path/to/file.ext -->` — full file (overwrite)
   - `<!-- patch: path/to/file.ext -->` — unified diff (partial update)

2. **Marker syntax**:
   - Exactly one space after `<!-- file:` or `<!-- patch:` and one space before `-->`.
   - On its own line, **immediately before** the opening fence.
   - Path is **project-relative** (`src/main.py`, not `/home/user/src/main.py`).
   - **Every project file or patch block MUST have a marker. No exceptions.**

3. **Heading** `### \`path/to/file.ext\``
   - Level-3 heading with the path in inline code backticks.
   - Must match the marker path **exactly**.
   - Descriptions go on a separate line between heading and marker.

4. **Language tag** on the fence is required (`python`, `bash`, `yaml`, `diff`, …).
   Patch blocks always use `diff`.

5. **Patch format**: standard unified diff with `--- a/path`, `+++ b/path`,
   `@@ -L,C +L,C @@` hunk headers, and context/add/remove lines.
   Minimum 3 context lines around each change.

### Fence depth

Outer fence must be **strictly longer** than any fence inside the content.
If the content has ``` (3 backticks), the outer fence must be ```` (4+).

### Choosing between file and patch

| Situation | Marker |
|---|---|
| New file | `<!-- file: -->` |
| Small file, most lines change | `<!-- file: -->` |
| Large file, few lines change | `<!-- patch: -->` |
| File under ~120 lines | Prefer `<!-- file: -->` |

### Patch accuracy

LLM-generated patches often have wrong `@@` line numbers.
To maximize success:

1. **Use anchor strings** near the change (function name, unique comment)
   rather than counting lines from the top.
2. **Increase context to 5-7 lines** for files over 200 lines.
3. **One hunk per conceptual change** — don't combine distant changes.
4. **Self-check**: re-read the original file and verify context lines exist.

### Multi-level nesting

When a Markdown file embeds other project files, every level must have
its own markers. Fence length increases by 1 backtick per nesting level.

### Preservation rules

When rewriting or translating a document with markers:
- **Every marker MUST be preserved** (path, syntax, type unchanged).
- If markers are missing — **add them**.
- **Never silently drop a marker.**

## Compliance checklist

Before every code block, verify:
1. Is this a project file? → heading + marker.
2. Full file or patch? → `<!-- file: -->` or `<!-- patch: -->`.
3. Heading and marker paths match?
4. Outer fence longer than inner fences?
5. Nested documents have their own markers?
"""
