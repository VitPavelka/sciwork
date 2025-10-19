# Delete mixin

:class:`sciwork.fs.delete.Delete` implements destructive operations with
consistent prompting, logging and ``dry_run`` handling.

## ``delete``

Remove a file, directory or symlink. Behavior is tuned by the following options:

- ``missing_ok`` — skip silently when the path is absent.
- ``recursive`` — required to remove non-empty directories.
- ``follow_symlinks`` — when ``True`` and the path is a symlink to a directory,
delete the target instead of the link (dangerous!; defaults to ``False``).
- ``confirm`` — prompt the user once before removal.

```python
fs.delete("output/cache", recursive=True, confirm=True)
```

When ``dry_run`` is active the method only logs the intended action.

## ``trash``

Move the target into the OS trash/recycle bin via :mod:`Send2Trash`. Mirrors the
options from ``delete`` but never removes the directory tree directly.

```python
fs.trash("screenshots/old.png", confirm=True)
```

This is the safest option when you want a reversible workflow.

## ``clear_folder``

Remove all entries inside ``folder`` while keeping the folder itself. Designed
for cleanup jobs that may involve many files.

Key arguments:

- ``recursive`` — recurse into subdirectories (default ``True``).
- ``include_hidden`` — skip hidden files when ``False``.
- ``pattern``/``antipattern``/``shell_pattern`` — filter entries by name.
- ``trash`` — send matches to trash instead of deleting permanently.
- ``follow_symlinks`` — follow directory symlinks when deleting permanently.
- ``missing_ok`` — ignore missing folders.
- ``ignore_errors`` — log and continue when deletions fail.
- ``confirm_if_over`` — estimate the number of candidates and request
confirmation when the threshold is reached.

```python
removed = fs.clear_folder(
    "staging",
    recursive=True,
    pattern=".tmp",
    confirm_if_over=200,
)
print(f"Remove {removed} temporary files")
```

The helper reuses :class:`~sciwork.fs.dirs.Dirs` to resolve the folder and
:mod:`Send2Trash` for reversible deletions. ``dry_run`` mode returns the count
that *would* be removed.