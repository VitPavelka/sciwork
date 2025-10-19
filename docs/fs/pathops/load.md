# Load mixin

:class:`sciwork.fs.load.Load` expose :meth:`any_data_loader`, a facade over
the specialized loaders available in ``sciwork.fs.loaders_base`` and related
parsers. It combines :class:`PathOpsBase`, the :class:`Classify 
<sciwork.fs.classify.Classify>` mixin and the concrete loader implementations.

## ``any_data_loader``

Open a structured data file and return either a :class:`pandas.DataFrame` or a
Python object, depending on the detected format. The method accepts a large set
of keyword arguments; loaders ignore options that do not apply to their format.

Supported types include:

- **Excel** (``.xlsx``, ``.xlsm``, ``.xls``) → DataFrame via ``openpyxl``.
- **CSV/TSV** → DataFrame with optional delimiter detection.
- **Plain text** → DataFrame or parsed rows.
- **JSON** → ``dict``/``list``.
- **XML** → DataFrame build from element dictionaries.
- **SIF** (Andor scientific Image Format) → DataFrame via ``_load_sif``.
- **UV/VIS SPC** → format-specific parser returning a DataFrame.

Key parameters:

- ``sheet_name`` — An Excel sheet to load. ``"choice"`` prompts the user to
pick a sheet via :class:`sciwork.console.Prompter` when available.
- ``encoding`` — override encoding for text formats (auto-detected otherwise; 
focused primarily on english/czech common language encodings).
- ``delimiter`` — enforce a specific delimiter for CSV/TXT.
- ``header`` — row index of the header when building DataFrames.
- ``dtype`` — pass custom dtypes to the pandas reader.
- ``include_hidden_rows`` — for Excel; include rows marked as hidden.
- ``force_type`` — bypass classification and load using a specific type label.

```python
df = fs.any_data_loader(
    "data/measurements.xlsx",
    sheet_name="Sheet1",
    include_hidden_rows=False,
)
```

If ``force_type`` is omitted the helper relies on
:meth:`Classify.classify_path <sciwork.fs.classify.Classify.classify_path>`
to determine which loader to call. Unknown extensions raise :class:`ValueError`.

Paths are resolved absolutely or relative to ``base_dir`` and missing file triggers a
:class:`FileNotFoundError` before any loader is attempted.