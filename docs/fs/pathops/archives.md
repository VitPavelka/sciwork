# Archives mixin
:class:`sciwork.fs.archives.Archives` provides safe extraction and compression
helpers for common archive formats.

## ``extract_archive``

Unpack an archive into ``extract_to`` (default: a sibling directory derived from
the archive name). Supported formats include ZIP, TAR/TAR.GZ/TAR.BZ2/TAR.XZ,
and RAR. The helper guards against directory traversal attacks when ``safe=True`` (default).

Important options:

- ``overwrite`` — allow extraction into a non-empty directory.
- ``password`` — unlock ZIP or RAR archives when supplied.
- ``safe`` — disable traversal protection when set to ``False``.

```python
fs.extract_archive(
    "dataset/images.zip",
    extract_to="dataset/images",
    overwrite=True,
)
```

The method picks the correct extractor automatically using
:meth:`detect_archive_type <sciwork.fs.archive_utils.detect_archive_type>` and
respects ``dry_run`` by logging the action.

## ``compress_to_archive``

Create an archive from a directory. Provide the source folder, choose a format
(``"zip"``, ``"tar"``, ``"gztar"``, ``"bztar"``, ``"xztar"``) and optionally
an explicit destination path.

```python
archive_path = fs.compress_to_archive(
    "reports/2024/run-03",
    arch_format="zip",
    overwrite=True
)
```

Key arguments:
- ``password`` — enable ZIP password protection (AES via :mod: `pyzipper`).
- ``include_hidden`` — include dot-files and directories (default: ``True``).
- ``compresslevel`` — tune compression strength for ZIP/BZ2.

When ``output_archive_path`` is omitted, the helper places the archive next to the
source directory using the appropriate suffix. Existing archives trigger a
:class:`FileExitsError` unless ``overwrite=True``. ``dry_run`` logs the planned
compression target and returns the resolved path.