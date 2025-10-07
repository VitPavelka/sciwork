# Printer

`Printer` focuses on readable console rendering of nested Python objects.

- Dicts print as `key: value` when the value is a scalar; nested values indent.
- Lists/Tuples/Sets display aligned index/labels
- Optional type hints (`(str)`, `(int)`...).
- Optional string truncation for very long text.
- ANSI colors when the output supports it.

## Minimal example

```python
from sciwork.console.printer import Printer

pr = Printer(use_color=True)
data = {"user": {"name": "Ada", "tags": ["math", "logic"]}, "active": True}
pr.printer(data, show_types=True, max_str=120)
```

# Colors and themes
`Printer` loads a small ANSI theme. If colors are not supported, it automatically falls back to plain text.

Ensure the theme file exists once:
```python
from sciwork.console.bootstrap import ensure_ansi_colors
ensure_ansi_colors(prefer="project", overwrite=False)
```

# Context manager
Temporarily change behavior (e.g., force color off):
```python
from sciwork.console.printer import Printer

pr = Printer(use_color=True)
with pr.use_color(False):
    pr.printer({"msg": "no colors here"})
# outside the block color setting is restored
```