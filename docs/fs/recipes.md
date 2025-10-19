# PathOps recipes

Use these short examples as building blocks for everyday filesystem automation.
Each snippet assumes an existing ``PathOps`` instance:

```python
from sciwork import PathOps

fs = PathOps.from_cwd()
```

## Ensure folders exist

```python
# Create ./data/raw (parents included)
fs.make_folder("data/raw")

# Ensure the parent folder for a report exists before writing
parent = fs.ensure_parent("reports/summary.csv")
print(f"Parent ready at: {parent}")
```

Need a scratch space? ``Dirs.temp_dir`` yields a temporary directory rooted at
``base_dir`` and cleans it up automatically.

```python
with fs.temp_dir(prefix="batch-") as tmp:
    print(f"Working in {tmp}")
    # ... write intermediate files ...
```

## Create or update files

```python
# Touch a file (create if missing)
fs.touch_file("logs/run.log")

# Force a fresh file and apply permissions
fs.create_file(
    "results/output.txt",
    op="w",                 # truncate if the file exists
    permissions=0o644
)
```

## Copy, move, and rename

```python
# Rename inside the same filesystem (EXDEV-safe)
fs.rename_path("data/raw.csv", "data/raw-2024.csv", overwrite=False)

# Copy a directory tree and keep metadata
target = fs.transfer(
    "models/checkpoints",
    "backups/",
    operation="copy",
    overwrite=True,
)
print(f"Copied to {target}")

# Move a file while creating parents automatically
fs.transfer(
    "reports/latest.pdf",
    "archive/2024/latest.pdf",
    operation="move",
    create_parents=True,
)
```

## Delete or trash safely

```python
# Permanently delete a file (ask first)
fs.delete("results/tmp.csv", confirm=True)

# Move a directory to the OS recycle bin
fs.trash("old/experiments", missing_ok=True)

# Clear a folder but keep the root dictionary
deleted = fs.clear_folder(
    "scratch",
    pattern=".tmp",
    include_hidden=False,
    confirm_if_over=100,
)
print(f"Removed {deleted} temporary files")
```

## Inspect and wait on directories

```python
# Quick existence & emptiness checks
root = fs.require_dir("incoming", create=True)
if fs.is_folder_empty(root):
    print("Nothing to process yet")

# Wait up to 2 minutes for new CSV files to appear
fs.wait_until_not_empty(
    root,
    timeout=120,
    pattern=".csv",
    file_count=True
)
```

List contents with filters or metadata:

```python
listing = fs.get_files_and_folders("data", recursive=False)
print(listing["files"])  # plain Path objects

rich = fs.get_contents(
    "data",
    recursive=True,
    include_hidden=False,
    shell_pattern="*.csv",
    return_absolute_paths=True
)
for path, meta in rich.items():
    print(path, meta["size"], meta["mtime"])  # bytes + POSIX timestamp
```

## Select entries interactively or by index
```python
choice = fs.select_paths(
    "data",
    path_type="files",
    allowed_exts=[".csv", ".tsv"],
)
print(f"User picked: {choice}")

# Collect multiple paths without prompting (indices are 1-based)
selected = fs.select_paths(
    "reports",
    multiple=True,
    default_indices=[1, 3, 5],
    return_indices=True,
)
```

## Archive and extract

```python
# Extract (with traversal protection by default)
output_dir = fs.extract_archive("downloads/archive.zip")

# Compress a folder into tar.gz
archive = fs.compress_to_archive(
    "results",
    arch_format="gztar",
    overwrite=True
)
print(f"Archive written to {archive}")
```

## Open in the system explorer

```python
fs.open_folder_and_wait("results", confirm_manual=False)
```

## Load tabular or structured data

```python
# Automatic format detection (CSV, Excel, JSON, ...)
df = fs.any_data_loader("data/sample.xlsx", sheet_name="Raw")
print(df.head())
```

The loader falls back to format-specific helpers provided by
:class:`sciwork.fs.load.BaseLoader`, so your ``PathOps`` instance can handle a
wide range of scientific file types from one entry point.