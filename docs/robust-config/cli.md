# CLI

```bash
robust-config -c inifile.ini --list-sections
robust-config -c inifile.ini --sections section --dump pretty
robust-config -c inifile.ini --interpolation none --validate \
    --schema-json schema.json --schema-template template

## Overrides:
Env: CONF__SECTION__KEYWORD=0
CLI: -o section.keyword=None -o section.keyword2="['x','y']"
```