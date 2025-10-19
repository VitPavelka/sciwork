# GetContents mixin

:class:`sciwork.fs.getcontents.GetContents` lists directory contents with rich
filtering and optional metadata extraction.

## ``get_files_and_folders``

Return two lists ``{"files": [...], "folders": [...]}`` containing paths that
match the supplied filters. Paths can be returned as absolute paths or as
relative entries (the default) using ``return_absolute_paths``.

Commonly used arguments:

- ``recursive`` — recurse into subdirectories.
- ``include_hidden`` — skip dot-files when ``False``.
- ``pattern``/``antipattern``/``shell_pattern`` — substring or glob filtering.
- ``follow_symlinks`` — allow recursion through directory symlinks.
- ``max_items`` — stop after collecting this many entries.
- ``older_than``/``newer_than`` — filter by modification time. Accept seconds
(float/int) ISO 8601 strings, human-friendly durations (``"2h"``, ``"7d"``)
or :class:`datetime.datetime` objects.

```python
listing = fs.get_files_and_folders(
    "data",
    recursive=True,
    pattern=".csv",
    return_absolute_paths=True,
)
print(listing["files"])
```

The helper runs lightweight checks and skips metadata building for speed.

## ``get_contents``

Return a mapping ``{path_str: metadata_dict}`` describing files and directories
that pass the filters. The metadata includes:

- ``type`` — ``"file"`` or ``"dir"``
- ``size`` — byte size for files.
- ``mtime`` — modification timestamp (float).
- ``stat`` — raw :class:`os.stat_result` (when available).
- ``exif`` — optional EXIF data for images when ``exif=True``.

Additional arguments mirror ``get_files_and_folders`` and add:

- ``confirm_if_over`` — prompt once when the listing grows beyond the threshold.
- ``ignore_errors`` — continue on permission errors or missing files.

```python
catalogue = fs.get_contents(
    "photos",
    recursive=False,
    exif=True,
    confirm_if_over=500,
)
for path_str, meta in catalogue.items():
    print(path_str, meta.get("exif", {})).get("DateTimeOriginal")
```

Use this variant when you need metadata-rich inspection, e.g., before bulk
processing or for reporting.