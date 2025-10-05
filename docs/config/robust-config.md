# Robust Config—Overview & Quick Start

The `sciwork.config` module centers around the `RobustConfig` class.

--- 

## Minimal INI

```ini
# example.ini
[main]
data_folderpath = ./data
general_keywords = foo,bar
header_rows = 0
```

## Template schema (JSON)
`configs/config_project.json`
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

## Load + validate
```python
from sciwork.config import RobustConfig

# Load one or more INI files
rc = RobustConfig().load_json_config("example.ini")

# Apply the 'data_handler' template to all currently loaded sections
rc.validate_with_schema_json("configs/config_project.json", template="data_handler")

# Or to specific sections only
rc.validate_with_schema_json(
    "configs/config_project.json", 
    template="data_handler", 
    sections=["main"]
)
```

---

## Types, defaults, choices
- type: "str" | "int" | "float" | "bool" | "null" | "list" | "dict" | "list[str]" ...
- required: boolean
- default: any JSON value (applied **before** validation if the key is missing)
- choices: an array → attaches a membership validator

### Example
```json
{
  "data_handler": {
    "sheet_names": {
      "type": ["str", "null"],
      "default": null,
      "choices": ["Sheet1", "Raw", null]
    }
  }
}
```

---

## Troubleshooting
- **Interpolation error with $ in INI**
    Escape the dollar as $$, or parse the INI with raw/disabled interpolation upstream
- **Missing required keys**
    Check section names and key spelling in INI/JSON; then re-run validation.