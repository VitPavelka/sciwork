# Open mixin

:class:`sciwork.fs.open.Open` exposes a single user-facing helper for opening
a folder in the system file explorer.

## ``open_folder_and_wait``

Resolve ``folder_path`` relative to ``base_dir`` and launch the platform-specific
explorer (``Explorer``, ``open``, ``xdg-open``/``gio``/``kde-open``/``gnome-open``).
The method optionally waits for the spawned process or prompts the user to 
confirm once the folder is open.

Arguments:

- ``confirm_manual`` — ask the user to continue (default ``True``). Uses
:class:`sciwork.console.Prompter` when available and falls back to ``input``.
- ``wait`` — block until the opener exits (best-effort; many GUI openers detach).
- ``timeout`` — optional timeout for the wait step.

```python
fs.open_folder_and_wait(
    "reports/lates",
    confirm_manual=False
)
```

With ``dry_run=True`` the method logs the action and returns the resolved path
without invoking the explorer. :class:`FileNotFoundError` and 
:class:`NotADirectoryError` guard incorrect inputs.