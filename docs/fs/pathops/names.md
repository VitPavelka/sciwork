# Names helper

The :mod:`sciwork.fs.names` module complements PathOps with a utility for building
timestamped filenames.

## ``create_timestamped_filename``

Generate a filename that embeds the current date (and optionally the time).
Use it when you need collision-free artifacts or audit-friendly exports.

Arguments:

- ``name`` — base filename (with or without extension).
- ``full`` — include time (``HH_MM_SS``) in addition to the date (default
``True``). Set ``False`` for date-only stamps.
- ``custom_format`` — supply a :func:`datetime.datetime.strftime` pattern.
- ``prepend_date`` — place the timestamp before the name instead of after it.
- ``tz`` — timezone for the timestamp (defaults to local time).
- ``keep_extension`` — retain the original extension (default ``True``).
- ``sep`` — separator inserted between the stem and time stamp (default ``"_"``).

```python
from sciwork.fs.names import create_timestamped_filename

filename = create_timestamped_filename("results.csv")
# → "results_2025_10_30_15_42_08.csv"
```

The helper normalizes whitespace to underscores and respects ``keep_extension``.
Combine it with :meth:`Create.ensure_parent <sciwork.fs.create.Create.ensure_parent>`
and :meth:`Create.create_file <sciwork.fs.create.Create.create_file>` to produce
uniquely named output files.