# Prompt & Confirm (Prompter)

`Prompter` adds interactive prompts on top of the color-aware `Printer`.
You usually won't instantiate it. Directly use the ready-made `Console`:

```python
from sciwork.console import Console

con = Console()

name = con.prompt("Your name", default="Anonymous", transform=str.strip)
wants = con.confirm("Proceed with processing?", default=True)

print("->", name, wants)
```

## Features
- Colorized prompt text and hint suffixes (choices, defaults).
- Optional validation and transformation pipeline.
- Robust Ctrl+C handling (raises `ValueError`)
- Test-friendly: inject `input_func` to simulate answers.

## Customizing colors
`Prompter` uses semantic roles mapped to the printer palette:
- `prompt` → typically green
- `hint` → typically blue
- `value` → reset/plain
- `error` → red
- `reset` → terminal reset

Adjust them by editing `ansi_colors.json`, or create it with:
```python
from sciwork.console import ensure_ansi_colors
ensure_ansi_colors(prefer="project")  # writes <cwd>/sciwork/configs/ansi_colors.json
```
