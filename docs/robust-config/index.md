# Robust Configs

Robust INI configuration loader with:

- Multiple file layering (base → env → CLI → in-memory)
- Section inheritance via `extends`
- Type-safe parsing (bool/int/float/None, lists, JSON-like)
- Env (`CONF__SECTION__KEY`) and CLI overrides
- Optional JSON **template** schema with defaults and validators
- Helpful errors + tiny CLI