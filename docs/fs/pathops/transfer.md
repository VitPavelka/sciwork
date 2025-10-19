# Transfer mixin

:class:`sciwork.fs.transfer.Transfer` orchestrates file and directory copies or
moves. It shares helpers with :class:`Create <sciwork.fs.create.Create>` and
:class:`Delete <sciwork.fs.delete.Delete>` to prepare targets and handle
conflicts.

## ``transfer``

Copy or move ``source`` to ``destination``. The method understands two broad
modes:

- ``operation=copy`` (default) — duplicate the source.
- ``operation=move`` — move the source, falling back to ``shutil.move`` when
cross-device operations fail.

Key arguments:

- ``overwrite`` — remove an existing target before copying/moving.
- ``preserve_metadata`` — choose between :func:`shutil.copy` and
:func:`shutil.copy2` for file copies (affects timestamps and permissions).
- ``create_parents`` — create missing destination parents.
- ``follow_symlinks`` — forward to :mod:`shutil` for file copies; directories
are always traversed.

```python
target = fs.transfer(
    "results/run-03/report.pdf",
    "archive/2024/",
    operation="copy",
    overwrite=True,
    preserve_metadata=True
)
```

When ``destination`` is an existing directory, the entry is placed inside it.
Otherwise, the path is treated as the exact target file/directory name. A
:class:`FileExistsError` is raised when ``overwrite=False`` and the target is
already present.

``dry_run`` logs the intended operation and returns resolved target without
performing any filesystem changes.