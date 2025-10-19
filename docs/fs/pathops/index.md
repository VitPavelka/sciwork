# PathOps overview

The :class:`sciwork.fs.pathops.PathOps` facade combines all filesystem mixins
into one object that shares a ``base_dir`` anchor, a global ``dry_run`` flag and
optional prompt helpers. The pages in this section document each mixin in
detail. Start here when you need a refresher on the basic instantiation.

## Constructing an instance

```python
from sciwork import PathOps

# Rooted at the current working directory
fs = PathOps.from_cwd()

# Or anchor to a specific project folder
fs = PathOps.at("/data/projects", dry_run=True)
```

Key construction helpers come from :class:`~sciwork.fs.base.PathOpsBase`:

- ``PathOps(base_dir=..., dry_run=False)`` — direct instantiation.
- ``PathOps.from_cwd()`` — convenience for :func:`pathlib.Path.cwd`.
- ``PathOps.at(path)`` — anchor to an arbitrary folder.

All relative arguments are resolved against ``base_dir``. You can peek at the
current configuration at any time:

```python
print(fs.base_dir)
print(fs.dry_run)

# or via the object itself
print(fs)
```

## Where to go next

Each major mixin has a dedicated page:

- [Paths](paths.md) — resolving, renaming and prompting for paths.
- [Dirs](dirs.md) — folder validation, emptiness checks and temporary
directories.
- [Create](create.md) — creating files and directories with consistent logging.
- [Delete](delete.md) — safe deletion, trashing and folder clearing.
- [Transfer](transfer.md) — copy/move pipelines with overwriting safeguards.
- [GetContents](getcontents.md) — listing folders with filters and metadata.
- [Select](select.md) — choosing paths programmatically or interactively.
- [Open](open.md) — launching the system file explorer.
- [TreeOps](treeops.md) — building folder/file trees from adjacency maps.
- [Archives](archives.md) — extraction and compression helpers.
- [Load](load.md) — ``any_data_loader`` facade for structured data files.
- [Names](names.md) — timestamped filename helper.

Recipe-style walkthrough remains in the [recipe overview](../recipes.md)



