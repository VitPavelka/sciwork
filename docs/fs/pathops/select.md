# Select mixin

:class:`sciwork.fs.select.Select` builds on the listing helpers to pick one or
many paths either programmatically or via interactive prompts.

## ``select_paths``
Return a single path or a list of paths from ``folder_path`` after applying
filters and sorting. When ``multiple=False`` (default) the function returns a
single :class:`pathlib.Path`; enabling ``multiple`` returns a list.

Important knobs:

- ``recursive`` — traverse subdirectories before selection.
- ``include_hidden`` / ``follow_symlinks`` — propagate to the underlying
directory listing.
- ``pattern``/``antipattern``/``shell_pattern`` — filter by name.
- ``sort_by`` — ``"name"`` (default), ``"mtime"``, ``"ctime"``, ``"size"`` or 
``"ext"`` (``"exts"`` is accepted as an alias).
- ``path_type`` — limit to ``"files"``, ``"folders"`` or ``"any"``.
- ``allowed_exts`` — restrict file selections by extension.
- ``descending`` — reverse the sort order.
- ``default_index`` / ``default_indices`` — bypass the interactive prompt by
pre-selecting indices (1-based).
- ``prompt_text`` — customize the question shown to the user when prompting.
- ``return_absolute_paths`` — return absolute paths instead of paths relative to
the selected root.

```python
# Pick a single CSV file by the most recent modification time.
csv_path = fs.select_paths(
    "data",
    pattern=".csv",
    sort_by="mtime",
)

# Select multiple image files using an interactive prompt
images = fs.select_paths(
    "photos",
    pattern=".jpg",
    multiple=True,
    allowed_exts=[".jpg", ".jpeg"]
)
```

When there is only a single candidate, the method returns it immediately. With a
console :class:`Prompter <sciwork.console.prompter.Prompter>` available, the
prompt displays numbered entries and validates indices; otherwise the fallback
relies on ``input``.