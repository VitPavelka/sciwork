# TreeOps mixin

:class:`sciwork.fs.trees.TreeOps` builds directory and file structures from a
simple adjacency dictionary. It is ideal for bootstrapping project layouts or
fixtures.

## ``build_tree``

Create directories and files described by ``tree_dict``. The dictionary must
contain a ``"parents"`` key width the list of root components. Each additional
key maps to the children for that component. Leaves that look like files (based
on known suffixes) are created using :meth:`Create.create_file`; other leaves
become directories.

```python
structure = {
    "parents": ["data"],
    "data": ["raw", "processed"],
    "raw": ["in.csv", "out.csv"],
    "processed": ["summary.xlsx"]
}
created = fs.build_tree(structure)
print(created["in.csv"])  # absolute path
```

Use ``file_mode`` to choose how files are created (``"a"``, ``"w"`` or ``"x"``).
The return value is a mapping ``{leaf_name: Path}`` containing the absolute path
for every created leaf. Invalid topologies (missing parents, cycles) raise
informative exceptions before any filesystem change occurs.