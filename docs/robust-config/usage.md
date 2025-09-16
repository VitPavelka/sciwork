# Usage (Library)

```python
from robust_config import RobustConfig, KeySpec

rc = (RobustConfig()
    .load(["inifile.ini"])
    .apply_env_overrides()
    .apply_overrides([]))

main = rc.section("section")
print(main["keyword"])

## Validation with JSON template
schema = rc.load_schema_from_json(
    "schema.json",
    template="template", # apply to all sections (or pass sections=[...])
    project=None
)
rc.validate(schema=schema)
```