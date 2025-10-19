# PathOps basics

The :class:`sciwork.fs.pathops.PathOps` class inherits from the full stack of
filesystem helpers (paths, directories, creation, deletion, transfer, archives,
loading, ...). It keeps the ergonomics of a single object while letting you reuse
the underlying :class:`~sciwork.fs.base.PathOpsBase` features such as
``base_dir``, ``dry_run`` and prompt integration.

## Constructing an instance

```python
from sciwork import PathOps

# rooted at the current working directory
fs = PathOps.from_cwd()

# or point to a specific project folder
fs = PathOps.at("/data/project", dry_run=True)
```

Key construction helpers come from :class:`PathOpsBase`:

- ``PathOps(base_dir=..., dry_run=False)`` - direct instantiation.
- ``PathOps.from_cwd()`` - convenience for ``Path.cwd()``.
- ``PathOps.at(path, dry_run=False)`` - anchor to an arbitrary folder.

All relative arguments are resolved against ``base_dir``. You can peek at the
current configuration at any time:

```python
print(fs.base_dir)
print(fs.dry_run)

# or just
print(fs)
```

## Resolving and validation paths

``PathOps`` exposes the ``Paths`` mixin for day-to-day path work:

- ``resolve_path(path)`` - join path segments relative to ``base_dir``.
- ``coerce_file_path(path)`` and ``coerce_folder_path(path)`` - resolve and
validate that a target exists and is of the expected type.
- ``rename_path(old, new, overwrite=False)`` - safe rename/move with EXDEV
fallback.
- ``prompt_path(kind="any", must_exist=True, ...)`` - interactive path prompt
with optional extension filtering and defaults.

## Dry-run friendly operations

Setting ``dry_run=True`` logs intended actions instead of modifying the
filesystem. All mixins respect the flag - copying, deleting, archive 
extraction, tree building, and more:

```python
fs = PathOps.at("~/Downloads", dry_run=True)
fs.transfer("reports.zip", "archive/reports.zip", operation="move")  # only logs
fs.delete("archive/old.log")  # no deletion
```

Dry-run mode is useful when rehearsing automation scripts or when you need to
preview the effect of recursive operations (e.g., ``clear_folder``).

## Prompt integration

Many operations can ask the user for confirmation or input. ``PathOps`` reuses
``input_func`` from :class:`PathOpsBase` and prefers the richer
:class:`sciwork.console.Prompter` when the console package is available. This
covers:

- ``prompt_path`` for asking the user to enter a file/folder path.
- ``delete(..., confirm=True)`` and ``trash(..., confirm=True)`` for destructive 
actions.
- ``clear_folder(confirm_if_over=...)`` to guard large cleanups.
- ``select_paths`` helpers that display enumerated menus and parse the
selection.

You can inject your own callable (e.g., a mock or GUI dialog) via 
``input_func`` when constructing ``PathOps``.

## Mixing in your own helpers

``PathOps`` is just a composed class. If you need additional behavior, inherit
from it and add your own methods or mixins:

```python
from sciwork import PathOps

class ProjectFS(PathOps):
    def dataset_dir(self, name: str):
        return self.resolve_path("datasets", name)

fs = ProjectFS.at("/srv/pipeline")
print(fs.dataset_dir("raw"))
```

All the base functionality remains available, and ``base_dir``/``dry_run`` still
propagate through your subclass.