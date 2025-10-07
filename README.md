# SciWork

SciWork is a small, modular toolkit for scientific workflows (Python ≥ 3.10).

## Features (current)
- Clean **config** handling (INI/JSON loading + validation via JSON schema templates)
- Lightweight **console** helpers (pretty printer, rules/lines, dot animation)
- Simple shared **logging** setup (console and optional file/rotation)

More modules (filesystem helpers, data handling, plotting) will follow.

**Full documentation:** https://vitpavelka.github.io/sciwork/

---

## Install (local dev)

### From GitHub (recommended for now)

```bash
pip install "git+https://github.com/vitpavelka/sciwork.git#egg=sciwork"
```


### Local editable install

```bash
# from the repo root
pip install -e .

# optional extras
pip install -e ".[docs]"  # docs toolchain
pip install -e ".[dev]"   # tests/linters (nothing there yet, heh)
```

---

## Features (snapshot)

- **Config** (`sciwork.config.RobustConfig`)
  - load one or many **INI** files (with a simple section inheritance)
  - overlay with **JSON** files
  - validate against a **JSON schema** (per-section or via reusable **template**)
  - collect and apply **defaults** from schema before validation

- **Console** (`sciwork.console.Console`)
  - compact **pretty printer** for nested structures (optional ANSI colors)
  - helpful **CLI output**: horizontal rules, dot-loading animation, duration formatting

- **Logging** (`sciwork.logutil.configure_logging`)
  - one-liner to get a shared app logger with console and optional file/rotation
  
---

## Project status
Early but stable enough for internal use. APIs may evolve (documented in the site's changelog once available).

---

## License
MIT © 2025 Vít Pavelka
