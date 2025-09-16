# JSON Template Schema

Minimal example (applied to all sections):

```json

{
  "data_handler": {
    "data_folderpath":      { "type": "str",                "required": true },
    "general_keywords":     { "type": ["list[str]","str"],  "default": [] },
    "general_antikeywords": { "type": ["list[str]","str"],  "default": [] },
    "header_rows":          { "type": ["int","null"],       "default": null },
    "sheet_names":          { "type": ["list[str]","str","null"], "default": null }
  }
}
```

```bash
# RUN
robust-config -c inifile.ini --validate
    --schema-json schema.json --schema-template data_handler
```