# Create mixin

The :class:`sciwork.fs.create.Create` covers creating directories and
files while respecting the shared ``base_dir`` and ``dry_run`` flags.

## ``ensure_parent``

Ensure that the parent directory of ``path`` exists, creating it when needed.
Returns the resolved parent path, making it easy to chain with file creation.

```python
target = fs.resolve_path("reports", "summary.csv")
parent = fs.ensure_parent(target)
```

The helper is routinely used by the other creation methods when
``create_parents=True``.

## ``touch_file``

Create the file if it is missing or update its modification time when it
already exists. Important switches:

- ``create_parents`` — ensure parent directories exist before touching.
- ``exist_ok`` — when ``False``, raises :class:`FileExistsError` if the file is already present.
- ``mode`` — optional permission bits applied after creation/update.

```python
fs.touch_file("logs/app.log", create_parents=True, mode=0o640)
```

## ``create_file``

Create an empty file using the supplied open mode (``'a'``, ``'w'`` or ``'x'``).
The method does not write data; it simply opens and closes the handle to ensure
the file exists.

```python
fs.create_file("data/output.json", op="w", create_parents=True)
```

When ``op='x'`` it will fail if the file already exists.
``permissions`` allows post-creation :func:`chmod` via ``Path.chmod``.

## ``make_folder``

Create a directory (and its parents) at ``path``. When the directory already
exists and ``exist_ok=True`` the call is a no-op, still returning the resolved
path.

```python
artifact_dir = fs.make_folder("artifacts/2024/run-03", exist_ok=False)
```

A :class `NotADirectoryError` is raised when a non-directory entry lives at the
requested colation. ``mode`` controls permissions for newly created folders
(where supported by the OS).