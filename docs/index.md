# SciWork

SciWork is a modular toolkit for scientific workflows. It currently features:

- **Config** — robust INI/JSON config creation, loading and validation (templates and defaults).
- **Console** — lightweight console helpers (pretty printer, rules/lines, dot animation)
- **Logging** — simple shared logging setup (console and optional file/rotation)

---

## Installation

```bash
# From source (editable)
git clone https://github.com/VitPavelka/sciwork.git
cd sciwork
pip install -e .[docs]

# From GitHub (non-editable)
pip install "git+https://github.com/VitPavelka/sciwork.git"
```

## Preview docs locally

```bash
mkdocs serve
```