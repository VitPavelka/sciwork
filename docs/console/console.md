# Console

`Console` is a thin wrapper around `Printer` that adds handy helpers for CLI UX.

## Rules (horizontal separators)

```python
from sciwork.console.console import Console

con = Console(use_color=True)
con.rule(80, prespace=True)  # prints an 80-char separator; optional empty line beforehand
```

## Dot loader (progress dots)
```python
from sciwork.console.console import Console

con = Console()
count = 0
for _ in range(12):
    count = con.dot_loading_animation(current=count, max_dots=4, left="Downloading", suffix="")
# prints: "Downloading...." cycling every 4 dots 
```

## Time formatting
```python
from sciwork.console.console import Console
from time import perf_counter

con = Console()

t0 = perf_counter()
# ... do something ...
t1 = perf_counter()
print(con.format_interval(t0, t1, ms=True))  # e.g. "1 min 12 s 315 ms"
```

## Colors still apply
All `Printer`-level color rules apply; `Console` reuses the same palette and detection logic.