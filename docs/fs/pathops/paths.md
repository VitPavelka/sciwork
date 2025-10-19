# Paths mixin

The :class:`sciwork.fs.paths.Paths` mixin adds user-facing helpers around
path resolution, renaming and interactive prompts. Methods respect the shared
``base_dir`` and ``dry_run`` flags inherited from
:class:`~sciwork.fs.base.PathOpsBase`.

## ``coerce_file_path``

Return an absolute :class:`pathlib.Path` that is safe to treat as a file path.
It resolves ``path`` relative to ``base_dir`` and guards against trailing slash
input that would otherwise point at a directory.

```python
fs = PathOps.at("/data")
log_file = fs.coerce_file_path("logs/app.log")
```

Use it whenever you accept a user-provided path that must behave like a file.
Combine with :meth:`Create.ensure_parent <sciwork.fs.create.Create.ensure_parent>`
to prepare containing folders before writing.

## ``coerce_folder_path``

Resolve ``path`` relative to ``base_dir`` and assert that it is an existing
directory. A :class:`NotADirectoryError` is raised when the target is missing
or points at a file.

```python
report_dir = fs.coerce_folder_path("reports/latest")
```

## ``resolve_path``

Join one or more path parts relative to ``base_dir`` (unless the first 
part is already absolute) and return the resolved absolute path. Empty
input returns the resolved ``base_dir`` itself.

```python
archive = fs.resolve_path("archives", "2024", "run-03.zip")
```

Because :meth:`Path.resolve` is called, symlinks are normalized and ``..``
segments are collapsed.

## ``rename_path``

Rename a file or folder to ``new_path``. When the destination is an existing
directory, the source is moved into it. The implementation prefers
:meth:`Path.rename` for atomic moves and falls back to :func:`shutil.move` on
EXDEV errors (cross-device moves).

Key options:
- ``overwrite`` — remove an existing destination before renaming.
- ``create_parents`` — create missing parent directories for the destination.

```python
fs.rename_path("results/output.csv", "archive/2024/output.csv", overwrite=True)
```

With ``dry_run=True``, the method logs the intended move without touching the
filesystem.

## ``prompt_path``
Prompt the user for a file or folder path and validate the response. The
method looks for a prompter in this order:

1. Explicit ``prompter`` argument.
2. ``self.prompt`` from :class:`sciwork.console.Prompter` (if available).
3. ``self.input_func`` fallback (set on construction).
4. Built-in :func:`input`.

The ``kind`` argument controls validation (``"file"``, ``"folder"`` or 
``"any"``) and ``allowed_exts`` can restrict filenames. ``default`` returns a
pre-selected path when the user submits an empty response.

```python
dataset = fs.prompt_path(
    kind="file",
    must_exist=True,
    allowed_exts=[".csv", ".tsv"],
    prompt="Select the dataset to analyze"
)
```

When ``must_exist=False`` the path may be new; obvious directory-looking input
(trailing slash) is rejected for ``kind="file"`` to avoid typos.