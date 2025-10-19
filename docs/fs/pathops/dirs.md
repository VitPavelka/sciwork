# Dirs mixin

:class:`sciwork.fs.dirs.Dirs` provides directory-centric utilities: validation,
emptiness checks and a convenience context manager for temporary folders. All
methods expect paths relative to ``base_dir`` by default and honour ``dry_run``
where applicable.

## ``require_dir``

Ensure the provided path exists and is a directory. With ``create=True`` missing
folders are created using :class:`~sciwork.fs.create.Create`.

```python
Logs = fs.require_dir("logs", create=True)
```

Use this when your workflow must guarantee a writable directory before continuing.

## ``try_get_dir``

Resolve ``folder_path`` and return it if it exists and is a directory. When the
path is missing and ``missing_ok=True`` the method returns ``None`` instead of
raising an exception.

```python
maybe_tmp = fs.try_get_dir("tmp", missing_ok=True)
```

It normalizes trivial inputs such as ``"."`` or the ``base_dir`` name to the
current base directory, making it safe to pass user-controlled values.

## ``is_folder_empty``

Check whether a folder contains any entries that pass optional name filters. By
default, all direct children (files and directories) are considered. Useful
parameters include:

- ``include_hidden`` — ignore dot-files when ``False``.
- ``pattern``/``antipattern`` — substring filters.
- ``shell_pattern`` — glob-style matching (e.g., ``"*.csv"``).
- ``files_only`` — restricts the scan to files.

```python
if fs.is_folder_empty("downloads", include_hidden=False):
    print("Nothing new to process")
```

## ``wait_until_not_empty``

Poll a folder until at least one entry matches the filters used by
``is_folder_empty``. The method raises :class:`TimeoutError` when the condition
is not met before ``timeout`` seconds have elapsed.

```python
fs.wait_until_not_empty(
    "incoming",
    timeout=120,
    poll_interval=2.0,
    pattern=".csv"
)
```

Permission errors encountered during polling are logged and ignored so that
other entries can still trigger the condition.

## ``temp_dir``

Context manager that yields a temporary directory inside ``folder_path`` (or the
system default when omitted). On exit the directory is removed when
``cleanup=True`` (default).

```python
with fs.temp_dir(prefix="analysis-") as scratch:
    produce_intermediate_files(Path(scratch))
# directory removed afterwards
```

The directory is created via :func:`tempfile.mkdtemp`, meaning it is unique per
invocation and suitable for concurrent workflows.