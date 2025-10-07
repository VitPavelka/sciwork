# Config module

The `sciwork.config` package provides a **robust configuration system**:

- Load one or more **INI** files into typed Python values
- Overlay/merge **JSON** files for overrides
- Optional section inheritance via `extends`
- Validate against **JSON templates** (types, required keys, defaults, choices)
- Clear, actionable error messages

- Start with **Robust Config** for a quick start or jump to the **API Reference**. 

---

## Quick start

```python
from sciwork.config import RobustConfig

rc = RobustConfig().load_ini_config("example.ini")
rc.validate_with_schema_json("configs/config_project.json", template="data_handler")
```

Template JSON describes expected keys/types/defaults once (reusable across many sections)
Validation applies defaults first, then checks required keys, types, and optional choices

See the **Robust Config** page for full examples.