# SciWork

SciWork is a small, modular toolkit for scientific workflows.  
Right now the main focus is **Config** — robust loading and validating of INI/JSON configs (with schema templates & defaults). More modules (filesystem helpers, console utilities, data/math) will follow.

## Features (current)
- `sciwork.config.RobustConfig`
  - load one or many **INI** files (with section inheritance)  
  - overlay with **JSON** files
  - validate against **JSON schema** (per-section or via reusable **template**)
  - apply **defaults** from the schema before validation
- `sciwork.logutil.configure_logging`
  - one-liner to set up a shared app logger with console and optional file/rotation

## Install (local dev)
```bash
# from the repo root
pip install -e .
```

Python ≥ 3.10 is required.

## Quickstart

```python
from sciwork.config import RobustConfig

# 1) load INI
rc = RobustConfig().load_ini_config("example.ini")

# 2) validate using a template from JSON
rc.validate_with_schema_json(
    "configs/config_project.json",
    template="data_handler"         # name of the template object in JSON
)

# Optionally: overlay JSON values first
rc.load_json_config("configs/extra.json").validate_with_schema_json(
    "configs/config_project.json",
    template="data_handler"
)

# Inspect
print(rc)           # human-friendly summary
data = rc.to_dict() # use in your code
```

Example of a **template** schema (`configs/config_project.json`):
```json
{
  "data_handler": {
    "data_folderpath": {"type": "str", "required": true},
    "general_keywords": {"type": "str", "required": true},
    "general_antikeywords": {"type": "str", "required": true},
    "header_rows": {"type": ["int", "null"], "default": null},
    "sheet_names": {"type": ["str", "null"], "default": null}
  }
}
```

## Logging (optional)
```python
from sciwork.logutil import configure_logging

log = configure_logging(
    name="sciwork",
    console_level="INFO",
    file_path="logs/sciwork.log",   # or None
    rotate=True                     # RotatingFileHandler if file_path is set
)
log.info("hello from SciWork!")
```

## Docs
```bash
pip install -e ".[docs]"
mkdocs serve
```

## Testing
```bash
pip install -e ".[dev]"
pytest -q
```

## License
MIT © 2025 Vít Pavelka
