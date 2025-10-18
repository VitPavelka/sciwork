# Console (overview)

Utilities for clean, readable console output:

- **Printer** — pretty-print nested structures with optional ANSI colors.
- **Console** — thin wrapper around `Printer` with extra helpers (rules, dot loader, timers).
- **Bootstrap** — generate `ansi_colors.json` once (project- or user-scoped).

## Quickstart

```python
from sciwork import Printer

pr = Printer(use_color=True)  # falls back to plain text if colors unsupported
pr.printer({"a": 1, "b": ["x", "y", {"z": 3}]}, show_types=True)
```
or
```python
from sciwork import Console

con = Console()
con.printer(...)
```

## Prompts & Console convenience
`Console` already includes the mixin `Prompter` and is exported at top-level
```python
from sciwork import Console
con = Console()
val = con.prompt("Give me a value", choices=["a", "b", "c"], default="b")
ok = con.confirm("Confirm", default=True)
```

## Console wrapper
```python
from sciwork import Console

con = Console(use_color=True)
con.rule(width=60)
count = 0
for _ in range(12):
    count = con.dot_loading_animation(current_count=count, max_dots=4, left="Downloading")
con.rule()
```

## Where is the color theme stored?
- Project scope: `./sciwork/configs/ansi_colors.json`
- User scope: `~/.config/sciwork/ansi_colors.json` (Windows: `%APPDATA%\sciwork\ansi_colors.json`)

Use `ensure_ansi_colors(prefer="user")` to switch (See more in `Printer` documentation).



